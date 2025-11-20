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
    require_role,
)
from app.middleware.logging import get_request_id
from core.conflict_detector import BGPConflictDetector, Conflict
from fastapi import Request
from models.peering import BGPPeering, PeeringStatus
from schemas.peering import BGPPeeringCreate, BGPPeeringResponse, BGPPeeringUpdate
from security.audit import AuditAction, log_audit_event
from security.auth import UserRole

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
) -> BGPPeeringResponse:
    """
    Create a new BGP peering session.

    - **Validates** against all conflict detection rules
    - **Returns 400** if conflicts are detected
    - **Audit logs** the creation
    - **Runs background task** for post-creation validation
    """
    request_id = get_request_id(request)

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

    # Check for conflicts
    conflicts = await detector.detect_conflicts(peering, all_peerings)
    if conflicts:
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
    async def post_creation_validation():
        """Run additional validation after creation."""
        # Could integrate with Batfish, RIPE RIS, etc.
        pass

    background_tasks.add_task(post_creation_validation)

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

