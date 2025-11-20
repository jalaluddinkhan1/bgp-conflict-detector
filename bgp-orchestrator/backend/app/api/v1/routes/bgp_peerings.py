"""
BGP peering CRUD API endpoints.
"""
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import (
    BatfishClientDep,
    ConflictDetector,
    CurrentUser,
    DbSession,
    RedisClient,
    RIPEClientDep,
    SuzieQClientDep,
    require_role,
)
from app.middleware.logging import get_request_id, logger
from core.conflict_detector import BGPConflictDetector, Conflict
from fastapi import Request
from models.peering import BGPPeering, PeeringStatus
from schemas.peering import BGPPeeringCreate, BGPPeeringResponse, BGPPeeringUpdate
from security.audit import AuditAction, log_audit_event
from security.auth import UserRole
from observability.metrics import (
    bgp_peerings_total,
    conflicts_detected,
    api_requests_total,
    api_latency,
    api_errors_total,
    conflict_detection_duration,
)
from time import time

# Rate limiter (10 requests per second per user)
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/bgp-peerings", tags=["BGP Peerings"])

# Add rate limit exception handler
router.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def serialize_peering(peering: BGPPeering) -> dict[str, Any]:
    """Convert SQLAlchemy model to response dict."""
    return {
        "id": peering.id,
        "name": peering.name,
        "local_asn": peering.local_asn,
        "peer_asn": peering.peer_asn,
        "peer_ip": peering.peer_ip,
        "hold_time": peering.hold_time,
        "keepalive": peering.keepalive,
        "device": peering.device,
        "interface": peering.interface,
        "status": peering.status.value if isinstance(peering.status, PeeringStatus) else peering.status,
        "address_families": peering.address_families,
        "routing_policy": peering.routing_policy,
        "created_at": peering.created_at,
        "updated_at": peering.updated_at,
        "created_by": peering.created_by,
        "updated_by": peering.updated_by,
    }


async def validate_peering_for_conflicts(
    peering: BGPPeering, all_peerings: list[BGPPeering], detector: BGPConflictDetector
) -> list[Conflict]:
    """Validate peering against all conflict detection rules."""
    conflicts = await detector.detect_conflicts(peering, all_peerings)
    return conflicts


@router.post("/", response_model=BGPPeeringResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/second")
async def create_peering(
    request: Request,
    peering_data: BGPPeeringCreate,
    background_tasks: BackgroundTasks,
    db: DbSession,
    user: CurrentUser,
    detector: ConflictDetector,
    redis: RedisClient,
    batfish: BatfishClientDep = None,
    suzieq: SuzieQClientDep = None,
    ripe_ris: RIPEClientDep = None,
) -> BGPPeeringResponse:
    """
    Create a new BGP peering session.

    - **Validates** against all conflict detection rules
    - **Returns 400** if conflicts are detected
    - **Audit logs** the creation
    - **Runs background task** for post-creation validation
    """
    start_time = time()
    request_id = get_request_id(request)
    
    # Log attempt
    logger.info(
        "peering_create_attempt",
        user=user.email,
        peering_name=peering_data.name,
        peer_ip=str(peering_data.peer_ip),
        peer_asn=peering_data.peer_asn,
        request_id=request_id,
    )

    # Get all existing peerings for conflict detection
    result = await db.execute(select(BGPPeering))
    all_peerings = result.scalars().all()

    # Create model instance
    peering = BGPPeering(
        name=peering_data.name,
        local_asn=peering_data.local_asn,
        peer_asn=peering_data.peer_asn,
        peer_ip=str(peering_data.peer_ip),
        hold_time=peering_data.hold_time,
        keepalive=peering_data.keepalive,
        device=peering_data.device,
        interface=peering_data.interface,
        status=peering_data.status.value,
        address_families=[af.value for af in peering_data.address_families],
        routing_policy=peering_data.routing_policy,
        created_by=user.email,
    )

    # Check for conflicts with timing
    conflict_start = time()
    conflicts = await detector.detect_conflicts(peering, all_peerings)
    conflict_duration = time() - conflict_start
    conflict_detection_duration.labels(rule_name="all_rules").observe(conflict_duration)
    
    if conflicts:
        # Track conflicts in metrics
        bgp_peerings_total.labels(status="rejected").inc()
        for conflict in conflicts:
            conflicts_detected.labels(
                type=conflict.type.value,
                severity=conflict.severity.value,
            ).inc()
        
        # Log conflicts
        logger.warning(
            "conflicts_detected",
            peering_name=peering_data.name,
            conflicts=[c.type.value for c in conflicts],
            request_id=request_id,
        )
        
        # Track API error
        api_errors_total.labels(
            method="POST",
            endpoint="/bgp-peerings",
            error_type="conflict_detected",
        ).inc()
        
        # Return conflicts in error response
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Conflicts detected in peering configuration",
                "conflicts": [
                    {
                        "type": c.type.value,
                        "severity": c.severity.value,
                        "description": c.description,
                        "affected_peers": c.affected_peers,
                        "recommended_action": c.recommended_action,
                    }
                    for c in conflicts
                ],
            },
        )

    # Save to database
    db.add(peering)
    await db.commit()
    await db.refresh(peering)

    # Audit log
    await log_audit_event(
        db_session=db,
        user_id=user.id,
        action=AuditAction.CREATE,
        table_name="bgp_peerings",
        record_id=peering.id,
        new_values=serialize_peering(peering),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
    )

    # Background task for additional validation
    async def post_creation_validation(
        peering_id: int,
        peering_name: str,
        peering_device: str,
        peering_peer_ip: str,
        peering_peer_asn: int,
        peering_local_asn: int,
        peering_keepalive: int,
        peering_hold_time: int,
        peering_status: str,
        batfish_client: BatfishClientDep,
        suzieq_client: SuzieQClientDep,
        ripe_ris_client: RIPEClientDep,
    ):
        """Run additional validation after creation using open source tools."""
        try:
            # 1. Validate with Batfish if available
            if batfish_client:
                try:
                    # Convert peering to config format for Batfish
                    config_text = f"""
router bgp {peering_local_asn}
 neighbor {peering_peer_ip} remote-as {peering_peer_asn}
 neighbor {peering_peer_ip} timers {peering_keepalive} {peering_hold_time}
"""
                    validation_result = await batfish_client.validate_bgp_config(config_text)
                    if not validation_result.valid:
                        # Log validation errors (could also send alerts)
                        print(f"Batfish validation errors for peering {peering_name}: {validation_result.errors}")
                except Exception as e:
                    print(f"Batfish validation failed: {e}")

            # 2. Validate prefix origin with RIPE RIS if available
            if ripe_ris_client:
                try:
                    # Check if we can get live updates (validates RIPE RIS is working)
                    # This could validate that the peer ASN is legitimate
                    # For now, just verify the client is functional
                    pass  # Placeholder - would need prefix information to validate origin
                except Exception as e:
                    print(f"RIPE RIS validation failed: {e}")

            # 3. Poll device state with SuzieQ if available
            if suzieq_client:
                try:
                    sessions = await suzieq_client.poll_bgp_sessions(peering_device)
                    # Match our peering with live session data
                    for session in sessions:
                        if session.peer == peering_peer_ip and session.peer_asn == peering_peer_asn:
                            # Update peering state if different
                            if session.state.value != peering_status:
                                print(f"Live session state mismatch: {session.state.value} vs {peering_status}")
                except Exception as e:
                    print(f"SuzieQ polling failed: {e}")
        except Exception as e:
            print(f"Post-creation validation error: {e}")

    background_tasks.add_task(
        post_creation_validation,
        peering_id=peering.id,
        peering_name=peering.name,
        peering_device=peering.device,
        peering_peer_ip=peering.peer_ip,
        peering_peer_asn=peering.peer_asn,
        peering_local_asn=peering.local_asn,
        peering_keepalive=peering.keepalive,
        peering_hold_time=peering.hold_time,
        peering_status=peering.status,
        batfish_client=batfish,
        suzieq_client=suzieq,
        ripe_ris_client=ripe_ris,
    )

    # Track successful creation
    bgp_peerings_total.labels(status="created").inc()
    duration = time() - start_time
    api_latency.labels(method="POST", endpoint="/bgp-peerings").observe(duration)
    api_requests_total.labels(method="POST", endpoint="/bgp-peerings", status_code=201).inc()
    
    logger.info(
        "peering_created",
        peering_id=peering.id,
        user=user.email,
        duration_ms=round(duration * 1000, 2),
        request_id=request_id,
    )

    return BGPPeeringResponse(**serialize_peering(peering))


@router.get("/", response_model=list[BGPPeeringResponse])
@limiter.limit("10/second")
async def list_peerings(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    device: str | None = Query(None, description="Filter by device name"),
    status_filter: PeeringStatus | None = Query(None, alias="status", description="Filter by status"),
    peer_asn: int | None = Query(None, description="Filter by peer ASN"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
) -> list[BGPPeeringResponse]:
    """
    List BGP peering sessions with pagination and filtering.

    - **Pagination**: `skip` and `limit` parameters
    - **Filters**: `device`, `status`, `peer_asn`
    - **Sort**: By `created_at` descending
    """
    start_time = time()
    query = select(BGPPeering)

    # Apply filters
    if device:
        query = query.where(BGPPeering.device == device)
    if status_filter:
        query = query.where(BGPPeering.status == status_filter.value)
    if peer_asn:
        query = query.where(BGPPeering.peer_asn == peer_asn)

    # Sort by created_at descending
    query = query.order_by(BGPPeering.created_at.desc())

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    peerings = result.scalars().all()

    duration = time() - start_time
    api_latency.labels(method="GET", endpoint="/bgp-peerings").observe(duration)
    api_requests_total.labels(method="GET", endpoint="/bgp-peerings", status_code=200).inc()

    return [BGPPeeringResponse(**serialize_peering(p)) for p in peerings]


@router.get("/{peering_id}", response_model=BGPPeeringResponse)
@limiter.limit("10/second")
async def get_peering(
    request: Request,
    peering_id: int,
    db: DbSession,
    user: CurrentUser,
) -> BGPPeeringResponse:
    """
    Retrieve a single BGP peering session by ID.
    """
    result = await db.execute(select(BGPPeering).where(BGPPeering.id == peering_id))
    peering = result.scalar_one_or_none()

    if peering is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peering with ID {peering_id} not found",
        )

    return BGPPeeringResponse(**serialize_peering(peering))


@router.put("/{peering_id}", response_model=BGPPeeringResponse)
@limiter.limit("10/second")
async def update_peering(
    request: Request,
    peering_id: int,
    peering_data: BGPPeeringUpdate,
    request: Request,
    db: DbSession,
    user: CurrentUser,
    detector: ConflictDetector,
) -> BGPPeeringResponse:
    """
    Update an existing BGP peering session.

    - **Conflict detection** on changes
    - **Audit logging** with old/new values
    - **Version tracking**
    """
    request_id = get_request_id(request)

    # Get existing peering
    result = await db.execute(select(BGPPeering).where(BGPPeering.id == peering_id))
    peering = result.scalar_one_or_none()

    if peering is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peering with ID {peering_id} not found",
        )

    # Store old values for audit
    old_values = serialize_peering(peering)

    # Update fields
    update_data = peering_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "address_families" and value is not None:
            setattr(peering, field, [af.value if hasattr(af, "value") else af for af in value])
        elif field == "status" and value is not None:
            setattr(peering, field, value.value if hasattr(value, "value") else value)
        elif field == "peer_ip" and value is not None:
            setattr(peering, field, str(value))
        elif value is not None:
            setattr(peering, field, value)

    peering.updated_by = user.email
    peering.updated_at = datetime.now(timezone.utc)

    # Check for conflicts with updated values
    result_all = await db.execute(select(BGPPeering))
    all_peerings = result_all.scalars().all()
    conflicts = await detector.detect_conflicts(peering, all_peerings)
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Conflicts detected in updated peering configuration",
                "conflicts": [
                    {
                        "type": c.type.value,
                        "severity": c.severity.value,
                        "description": c.description,
                        "recommended_action": c.recommended_action,
                    }
                    for c in conflicts
                ],
            },
        )

    await db.commit()
    await db.refresh(peering)

    # Audit log
    new_values = serialize_peering(peering)
    await log_audit_event(
        db_session=db,
        user_id=user.id,
        action=AuditAction.UPDATE,
        table_name="bgp_peerings",
        record_id=peering.id,
        old_values=old_values,
        new_values=new_values,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
    )

    return BGPPeeringResponse(**serialize_peering(peering))


@router.delete("/{peering_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/second")
async def delete_peering(
    request: Request,
    peering_id: int,
    db: DbSession,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> None:
    """
    Soft delete a BGP peering session.

    - **Requires ADMIN role**
    - **Audit logs** the deletion
    - **Cascades** to audit logs
    """
    request_id = get_request_id(request)

    # Get existing peering
    result = await db.execute(select(BGPPeering).where(BGPPeering.id == peering_id))
    peering = result.scalar_one_or_none()

    if peering is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peering with ID {peering_id} not found",
        )

    # Store values for audit
    old_values = serialize_peering(peering)

    # Soft delete (mark as disabled)
    peering.status = PeeringStatus.DISABLED.value
    peering.updated_by = current_user.email
    peering.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Audit log
    await log_audit_event(
        db_session=db,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        table_name="bgp_peerings",
        record_id=peering.id,
        old_values=old_values,
        new_values=serialize_peering(peering),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
    )

    return None


@router.post("/{peering_id}/validate", status_code=status.HTTP_200_OK)
@limiter.limit("5/second")
async def validate_peering_with_batfish(
    request: Request,
    peering_id: int,
    db: DbSession,
    user: CurrentUser,
    batfish: BatfishClientDep = None,
) -> dict[str, Any]:
    """
    Validate a BGP peering configuration using Batfish.
    
    - **Requires** Batfish to be configured and running
    - **Returns** validation results with errors and warnings
    """
    if not batfish:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Batfish service is not configured or unavailable",
        )

    # Get peering
    result = await db.execute(select(BGPPeering).where(BGPPeering.id == peering_id))
    peering = result.scalar_one_or_none()

    if peering is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peering with ID {peering_id} not found",
        )

    # Convert peering to config format for Batfish
    config_text = f"""
router bgp {peering.local_asn}
 neighbor {peering.peer_ip} remote-as {peering.peer_asn}
 neighbor {peering.peer_ip} timers {peering.keepalive} {peering.hold_time}
"""

    try:
        validation_result = await batfish.validate_bgp_config(config_text)
        return {
            "peering_id": peering_id,
            "peering_name": peering.name,
            "valid": validation_result.valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "issues": [
                {
                    "session_name": issue.session_name,
                    "issue_type": issue.issue_type,
                    "severity": issue.severity.value,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                }
                for issue in validation_result.issues
            ],
            "loops": [
                {
                    "loop_type": loop.loop_type,
                    "affected_prefixes": loop.affected_prefixes,
                    "as_path": loop.as_path,
                    "severity": loop.severity.value,
                    "description": loop.description,
                }
                for loop in validation_result.loops
            ],
            "summary": validation_result.summary,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batfish validation failed: {str(e)}",
        ) from e


@router.get("/{peering_id}/live-state", status_code=status.HTTP_200_OK)
@limiter.limit("10/second")
async def get_peering_live_state(
    request: Request,
    peering_id: int,
    db: DbSession,
    user: CurrentUser,
    suzieq: SuzieQClientDep = None,
) -> dict[str, Any]:
    """
    Get live BGP session state from SuzieQ for a peering.
    
    - **Requires** SuzieQ to be configured and running
    - **Returns** live session state from the device
    """
    if not suzieq:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SuzieQ service is not configured or unavailable",
        )

    # Get peering
    result = await db.execute(select(BGPPeering).where(BGPPeering.id == peering_id))
    peering = result.scalar_one_or_none()

    if peering is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peering with ID {peering_id} not found",
        )

    try:
        sessions = await suzieq.poll_bgp_sessions(peering.device)
        
        # Find matching session
        matching_session = None
        for session in sessions:
            if session.peer == peering.peer_ip and session.peer_asn == peering.peer_asn:
                matching_session = session
                break

        if not matching_session:
            return {
                "peering_id": peering_id,
                "peering_name": peering.name,
                "found": False,
                "message": "No matching live session found",
            }

        return {
            "peering_id": peering_id,
            "peering_name": peering.name,
            "found": True,
            "live_state": {
                "state": matching_session.state.value,
                "uptime": matching_session.uptime,
                "prefix_count": matching_session.prefix_count,
                "hold_time": matching_session.hold_time,
                "keepalive": matching_session.keepalive,
                "last_update": matching_session.last_update.isoformat() if matching_session.last_update else None,
            },
            "configured_state": {
                "status": peering.status,
                "hold_time": peering.hold_time,
                "keepalive": peering.keepalive,
            },
            "state_match": matching_session.state.value == peering.status,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"SuzieQ polling failed: {str(e)}",
        ) from e


@router.get("/{peering_id}/bgp-updates", status_code=status.HTTP_200_OK)
@limiter.limit("5/second")
async def get_peering_bgp_updates(
    request: Request,
    peering_id: int,
    db: DbSession,
    user: CurrentUser,
    ripe_ris: RIPEClientDep = None,
    limit: int = Query(10, ge=1, le=100, description="Maximum number of updates to return"),
) -> dict[str, Any]:
    """
    Get recent BGP updates from RIPE RIS for a peering's prefix/ASN.
    
    - **Requires** RIPE RIS to be enabled
    - **Returns** recent BGP announcements/withdrawals
    """
    if not ripe_ris:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RIPE RIS service is not enabled or unavailable",
        )

    # Get peering
    result = await db.execute(select(BGPPeering).where(BGPPeering.id == peering_id))
    peering = result.scalar_one_or_none()

    if peering is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peering with ID {peering_id} not found",
        )

    try:
        # Get historical data for the peer ASN (last hour)
        from datetime import timedelta
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=1)

        events = await ripe_ris.get_historical_data(
            start_time=start_time,
            end_time=end_time,
            collectors=["rrc00", "rrc01"],  # Use a couple of collectors
        )

        # Filter events related to this peering (by peer ASN)
        relevant_events = [
            event
            for event in events
            if event.peer_asn == peering.peer_asn or (event.origin_as and event.origin_as == peering.peer_asn)
        ][:limit]

        return {
            "peering_id": peering_id,
            "peering_name": peering.name,
            "peer_asn": peering.peer_asn,
            "events_found": len(relevant_events),
            "events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "peer_ip": event.peer_ip,
                    "peer_asn": event.peer_asn,
                    "prefix": event.prefix,
                    "as_path": event.as_path,
                    "origin_as": event.origin_as,
                    "next_hop": event.next_hop,
                    "event_type": event.event_type.value,
                    "communities": event.communities,
                }
                for event in relevant_events
            ],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RIPE RIS query failed: {str(e)}",
        ) from e

