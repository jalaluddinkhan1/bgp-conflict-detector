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

    # Get all existing peerings for conflict detection (exclude soft-deleted)
    result = await db.execute(select(BGPPeering).where(BGPPeering.is_deleted == False))
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
    try:
        db.add(peering)
        await db.commit()
        await db.refresh(peering)
    except Exception as e:
        await db.rollback()
        logger.error(
            "peering_creation_failed",
            error=str(e),
            peering_name=peering_data.name,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create peering: {str(e)}",
        ) from e

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
                        logger.warning(
                            "batfish_validation_errors",
                            peering_name=peering_name,
                            errors=validation_result.errors,
                        )
                except Exception as e:
                    logger.error("batfish_validation_failed", error=str(e), peering_name=peering_name)

            if ripe_ris_client:
                try:
                    pass
                except Exception as e:
                    logger.error("ripe_ris_validation_failed", error=str(e), peering_name=peering_name)

            if suzieq_client:
                try:
                    sessions = await suzieq_client.poll_bgp_sessions(peering_device)
                    for session in sessions:
                        if session.peer == peering_peer_ip and session.peer_asn == peering_peer_asn:
                            if session.state.value != peering_status:
                                logger.warning(
                                    "live_session_state_mismatch",
                                    peering_name=peering_name,
                                    configured_state=peering_status,
                                    live_state=session.state.value,
                                )
                except Exception as e:
                    logger.error("suzieq_polling_failed", error=str(e), peering_name=peering_name)
        except Exception as e:
            logger.error("post_creation_validation_error", error=str(e), peering_name=peering_name)

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
    query = select(BGPPeering).where(BGPPeering.is_deleted == False)

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


@router.post("/bulk", response_model=list[BGPPeeringResponse], status_code=status.HTTP_201_CREATED)
@limiter.limit("5/second")  # Lower rate limit for bulk operations
async def bulk_create_peerings(
    request: Request,
    peerings: list[BGPPeeringCreate],
    db: DbSession,
    user: CurrentUser,
    detector: ConflictDetector,
) -> list[BGPPeeringResponse]:
    """
    Bulk create BGP peering sessions in a single transaction.

    - **Validates** all peerings before creating any
    - **Runs in single transaction** - all or nothing
    - **Returns 400** if any conflicts are detected
    - **Audit logs** the bulk creation
    - **Maximum 100 peerings** per bulk operation
    """
    from typing import List
    
    request_id = get_request_id(request)
    start_time = time()

    if len(peerings) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one peering is required for bulk creation",
        )
    
    if len(peerings) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 peerings allowed per bulk operation",
        )

    # Get all existing peerings for conflict detection
    result = await db.execute(select(BGPPeering).where(BGPPeering.is_deleted == False))
    all_peerings = result.scalars().all()

    # Validate all peerings before creating any
    created_peerings: List[BGPPeering] = []
    
    try:
        async with db.begin():
            for peering_data in peerings:
                # Create peering object
                peering = BGPPeering(
                    name=peering_data.name,
                    local_asn=peering_data.local_asn,
                    peer_asn=peering_data.peer_asn,
                    peer_ip=str(peering_data.peer_ip),
                    hold_time=peering_data.hold_time,
                    keepalive=peering_data.keepalive,
                    device=peering_data.device,
                    interface=peering_data.interface,
                    status=peering_data.status.value if hasattr(peering_data.status, "value") else peering_data.status,
                    address_families=[af.value if hasattr(af, "value") else af for af in peering_data.address_families],
                    routing_policy=peering_data.routing_policy,
                    created_by=user.email,
                    is_deleted=False,
                )

                # Check for conflicts
                conflicts = await detector.detect_conflicts(peering, all_peerings + created_peerings)
                if conflicts:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "message": f"Conflicts detected for peering '{peering_data.name}'",
                            "peering_name": peering_data.name,
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

                db.add(peering)
                created_peerings.append(peering)
                all_peerings.append(peering)  # Add to context for next iteration

            # Commit all at once
            await db.commit()

            # Refresh all created peerings
            for peering in created_peerings:
                await db.refresh(peering)

            # Audit log for bulk creation
            for peering in created_peerings:
                await log_audit_event(
                    db_session=db,
                    user_id=user.id,
                    action=AuditAction.CREATE,
                    table_name="bgp_peerings",
                    record_id=peering.id,
                    old_values=None,
                    new_values=serialize_peering(peering),
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                    request_id=request_id,
                )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            "bulk_peering_creation_failed",
            error=str(e),
            user=user.email,
            count=len(peerings),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk creation failed: {str(e)}",
        ) from e

    duration = time() - start_time
    api_latency.labels(method="POST", endpoint="/bgp-peerings/bulk").observe(duration)
    api_requests_total.labels(method="POST", endpoint="/bgp-peerings/bulk", status_code=201).inc()
    bgp_peerings_total.labels(status="created").inc(len(created_peerings))

    logger.info(
        "bulk_peerings_created",
        count=len(created_peerings),
        user=user.email,
        duration_ms=round(duration * 1000, 2),
        request_id=request_id,
    )

    return [BGPPeeringResponse(**serialize_peering(p)) for p in created_peerings]


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
    result = await db.execute(
        select(BGPPeering).where(BGPPeering.id == peering_id, BGPPeering.is_deleted == False)
    )
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
    result = await db.execute(
        select(BGPPeering).where(BGPPeering.id == peering_id, BGPPeering.is_deleted == False)
    )
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

    # Check for conflicts with updated values (exclude soft-deleted)
    result_all = await db.execute(select(BGPPeering).where(BGPPeering.is_deleted == False))
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

    try:
        await db.commit()
        await db.refresh(peering)
    except Exception as e:
        await db.rollback()
        logger.error(
            "peering_update_failed",
            error=str(e),
            peering_id=peering_id,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update peering: {str(e)}",
        ) from e

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
    result = await db.execute(
        select(BGPPeering).where(BGPPeering.id == peering_id, BGPPeering.is_deleted == False)
    )
    peering = result.scalar_one_or_none()

    if peering is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peering with ID {peering_id} not found",
        )

    # Store values for audit
    old_values = serialize_peering(peering)

    # Soft delete (set is_deleted flag)
    peering.is_deleted = True
    peering.deleted_at = datetime.now(timezone.utc)
    peering.deleted_by = current_user.email
    peering.status = PeeringStatus.DISABLED.value
    peering.updated_by = current_user.email
    peering.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(
            "peering_deletion_failed",
            error=str(e),
            peering_id=peering_id,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete peering: {str(e)}",
        ) from e

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
    result = await db.execute(
        select(BGPPeering).where(BGPPeering.id == peering_id, BGPPeering.is_deleted == False)
    )
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
    result = await db.execute(
        select(BGPPeering).where(BGPPeering.id == peering_id, BGPPeering.is_deleted == False)
    )
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
    result = await db.execute(
        select(BGPPeering).where(BGPPeering.id == peering_id, BGPPeering.is_deleted == False)
    )
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


@router.post("/bulk-delete", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/second")
async def bulk_delete_peerings(
    request: Request,
    peering_ids: list[int],
    db: DbSession,
    user: CurrentUser,
    current_user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN))],
) -> None:
    """
    Bulk delete BGP peering sessions.
    
    - **Requires ADMIN role**
    - **Soft deletes** all peerings in the list
    - **Audit logs** the bulk deletion
    """
    request_id = get_request_id(request)
    
    if not peering_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one peering ID is required",
        )
    
    if len(peering_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 peerings allowed per bulk delete operation",
        )
    
    # Get peerings
    result = await db.execute(
        select(BGPPeering).where(
            BGPPeering.id.in_(peering_ids),
            BGPPeering.is_deleted == False
        )
    )
    peerings = result.scalars().all()
    
    if len(peerings) != len(peering_ids):
        found_ids = {p.id for p in peerings}
        missing_ids = set(peering_ids) - found_ids
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peerings not found: {sorted(missing_ids)}",
        )
    
    # Soft delete all peerings
    now = datetime.now(timezone.utc)
    for peering in peerings:
        old_values = serialize_peering(peering)
        peering.is_deleted = True
        peering.deleted_at = now
        peering.deleted_by = current_user.email
        peering.status = PeeringStatus.DISABLED.value
        peering.updated_by = current_user.email
        peering.updated_at = now
        
        # Audit log each deletion
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
    
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(
            "bulk_peering_deletion_failed",
            error=str(e),
            user=current_user.email,
            count=len(peerings),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk deletion failed: {str(e)}",
        ) from e
    
    logger.info(
        "bulk_peerings_deleted",
        count=len(peerings),
        user=current_user.email,
        request_id=request_id,
    )
    
    return None


@router.put("/bulk-update", response_model=list[BGPPeeringResponse])
@limiter.limit("5/second")
async def bulk_update_peerings(
    request: Request,
    peering_ids: list[int],
    updates: dict[str, Any],
    db: DbSession,
    user: CurrentUser,
    detector: ConflictDetector,
) -> list[BGPPeeringResponse]:
    """
    Bulk update BGP peering sessions.
    
    - **Validates** all updates
    - **Runs in single transaction** - all or nothing
    - **Audit logs** the bulk update
    - **Maximum 100 peerings** per bulk operation
    """
    request_id = get_request_id(request)
    
    if not peering_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one peering ID is required",
        )
    
    if len(peering_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 peerings allowed per bulk update operation",
        )
    
    # Get all peerings
    result = await db.execute(
        select(BGPPeering).where(
            BGPPeering.id.in_(peering_ids),
            BGPPeering.is_deleted == False
        )
    )
    peerings = result.scalars().all()
    
    if len(peerings) != len(peering_ids):
        found_ids = {p.id for p in peerings}
        missing_ids = set(peering_ids) - found_ids
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peerings not found: {sorted(missing_ids)}",
        )
    
    # Store old values and apply updates
    old_values_list = []
    for peering in peerings:
        old_values = serialize_peering(peering)
        old_values_list.append(old_values)
        
        # Apply updates
        for field, value in updates.items():
            if hasattr(peering, field) and value is not None:
                if field == "address_families":
                    setattr(peering, field, [af.value if hasattr(af, "value") else af for af in value])
                elif field == "status":
                    setattr(peering, field, value.value if hasattr(value, "value") else value)
                elif field == "peer_ip":
                    setattr(peering, field, str(value))
                else:
                    setattr(peering, field, value)
        
        peering.updated_by = user.email
        peering.updated_at = datetime.now(timezone.utc)
    
    # Check for conflicts with updated values
    result_all = await db.execute(select(BGPPeering).where(BGPPeering.is_deleted == False))
    all_peerings = result_all.scalars().all()
    
    for peering in peerings:
        conflicts = await detector.detect_conflicts(peering, [p for p in all_peerings if p.id != peering.id])
        if conflicts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": f"Conflicts detected for peering '{peering.name}'",
                    "peering_id": peering.id,
                    "peering_name": peering.name,
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
    
    # Audit log and commit
    try:
        for peering, old_values in zip(peerings, old_values_list):
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
        
        await db.commit()
        for peering in peerings:
            await db.refresh(peering)
    except Exception as e:
        await db.rollback()
        logger.error(
            "bulk_peering_update_failed",
            error=str(e),
            user=user.email,
            count=len(peerings),
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk update failed: {str(e)}",
        ) from e
    
    logger.info(
        "bulk_peerings_updated",
        count=len(peerings),
        user=user.email,
        request_id=request_id,
    )
    
    return [BGPPeeringResponse(**serialize_peering(p)) for p in peerings]


@router.get("/export/csv")
@limiter.limit("10/second")
async def export_peerings_csv(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    device: str | None = Query(None),
    status_filter: PeeringStatus | None = Query(None, alias="status"),
) -> Any:
    """
    Export BGP peerings as CSV.
    
    - **Returns** CSV file download
    - **Supports filtering** by device and status
    """
    import csv
    from io import StringIO
    
    query = select(BGPPeering).where(BGPPeering.is_deleted == False)
    
    if device:
        query = query.where(BGPPeering.device == device)
    if status_filter:
        query = query.where(BGPPeering.status == status_filter.value)
    
    query = query.order_by(BGPPeering.created_at.desc())
    
    result = await db.execute(query)
    peerings = result.scalars().all()
    
    # Create CSV
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Name", "Local ASN", "Peer ASN", "Peer IP", "Device", "Interface",
        "Status", "Hold Time", "Keepalive", "Address Families", "Created At", "Updated At"
    ])
    
    # Write data
    for peering in peerings:
        writer.writerow([
            peering.id,
            peering.name,
            peering.local_asn,
            peering.peer_asn,
            peering.peer_ip,
            peering.device,
            peering.interface or "",
            peering.status.value if isinstance(peering.status, PeeringStatus) else peering.status,
            peering.hold_time,
            peering.keepalive,
            ",".join(peering.address_families) if peering.address_families else "",
            peering.created_at.isoformat() if peering.created_at else "",
            peering.updated_at.isoformat() if peering.updated_at else "",
        ])
    
    from fastapi.responses import Response
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="bgp-peerings-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}.csv"'
        },
    )


@router.get("/export/json")
@limiter.limit("10/second")
async def export_peerings_json(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    device: str | None = Query(None),
    status_filter: PeeringStatus | None = Query(None, alias="status"),
) -> Any:
    """
    Export BGP peerings as JSON.
    
    - **Returns** JSON file download
    - **Supports filtering** by device and status
    """
    import json
    
    query = select(BGPPeering).where(BGPPeering.is_deleted == False)
    
    if device:
        query = query.where(BGPPeering.device == device)
    if status_filter:
        query = query.where(BGPPeering.status == status_filter.value)
    
    query = query.order_by(BGPPeering.created_at.desc())
    
    result = await db.execute(query)
    peerings = result.scalars().all()
    
    # Serialize peerings
    data = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "count": len(peerings),
        "peerings": [serialize_peering(p) for p in peerings],
    }
    
    from fastapi.responses import Response
    json_content = json.dumps(data, indent=2, default=str)
    
    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="bgp-peerings-{datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")}.json"'
        },
    )


@router.get("/topology")
@limiter.limit("10/second")
async def get_peerings_topology(
    request: Request,
    db: DbSession,
    user: CurrentUser,
) -> dict[str, Any]:
    """
    Get BGP peerings topology graph for visualization.
    
    - **Returns** graph data with nodes (devices/ASNs) and edges (peerings)
    - **Format**: { nodes: [...], edges: [...] }
    """
    result = await db.execute(
        select(BGPPeering).where(BGPPeering.is_deleted == False)
    )
    peerings = result.scalars().all()
    
    # Build graph
    nodes_set = set()
    edges = []
    
    for peering in peerings:
        # Add nodes (devices)
        local_node_id = f"device_{peering.device}"
        local_node = {
            "id": local_node_id,
            "label": peering.device,
            "type": "device",
            "group": peering.local_asn,
        }
        nodes_set.add((local_node_id, local_node))
        
        # Add peer node (represented by peer IP and ASN)
        peer_node_id = f"peer_{peering.peer_ip}"
        peer_node = {
            "id": peer_node_id,
            "label": f"{peering.peer_ip} (AS{peering.peer_asn})",
            "type": "peer",
            "group": peering.peer_asn,
        }
        nodes_set.add((peer_node_id, peer_node))
        
        # Add edge (peering relationship)
        edge = {
            "id": f"edge_{peering.id}",
            "source": local_node_id,
            "target": peer_node_id,
            "label": peering.name,
            "status": peering.status.value if isinstance(peering.status, PeeringStatus) else peering.status,
            "peer_asn": peering.peer_asn,
            "local_asn": peering.local_asn,
        }
        edges.append(edge)
    
    nodes = [node[1] for node in nodes_set]
    
    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "total_peerings": len(peerings),
        },
    }

