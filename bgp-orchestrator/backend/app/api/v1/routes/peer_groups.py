"""
Peer Group CRUD API endpoints.
"""
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from models.entities import PeerGroup, Tag
from schemas.entities import (
    PeerGroupCreate,
    PeerGroupResponse,
    PeerGroupUpdate,
    TagResponse,
)

router = APIRouter(prefix="/peer-groups", tags=["Peer Groups"])


def serialize_peer_group(pg: PeerGroup) -> dict[str, Any]:
    """Convert SQLAlchemy model to response dict."""
    return {
        "id": pg.id,
        "name": pg.name,
        "device_id": pg.device_id,
        "description": pg.description,
        "enabled": pg.enabled,
        "autonomous_system_id": pg.autonomous_system_id,
        "import_policy_id": pg.import_policy_id,
        "export_policy_id": pg.export_policy_id,
        "source_ip_address": pg.source_ip_address,
        "source_interface": pg.source_interface,
        "template_id": pg.template_id,
        "created_at": pg.created_at,
        "updated_at": pg.updated_at,
        "tags": [TagResponse.model_validate(tag) for tag in (pg.tags or [])],
        "autonomous_system": {
            "id": pg.autonomous_system.id,
            "asn": pg.autonomous_system.asn,
            "description": pg.autonomous_system.description,
            "status": pg.autonomous_system.status,
        } if pg.autonomous_system else None,
        "import_policy": {
            "id": pg.import_policy.id,
            "name": pg.import_policy.name,
            "type": pg.import_policy.type,
        } if pg.import_policy else None,
        "export_policy": {
            "id": pg.export_policy.id,
            "name": pg.export_policy.name,
            "type": pg.export_policy.type,
        } if pg.export_policy else None,
    }


@router.get("/", response_model=list[PeerGroupResponse])
async def list_peer_groups(
    db: DbSession,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[PeerGroupResponse]:
    """List all peer groups with pagination."""
    result = await db.execute(
        select(PeerGroup)
        .options(
            selectinload(PeerGroup.tags),
            selectinload(PeerGroup.autonomous_system),
            selectinload(PeerGroup.import_policy),
            selectinload(PeerGroup.export_policy),
        )
        .offset(skip)
        .limit(limit)
        .order_by(PeerGroup.name)
    )
    peer_groups = result.scalars().all()
    return [PeerGroupResponse(**serialize_peer_group(pg)) for pg in peer_groups]


@router.get("/{peer_group_id}", response_model=PeerGroupResponse)
async def get_peer_group(
    peer_group_id: int,
    db: DbSession,
    user: CurrentUser,
) -> PeerGroupResponse:
    """Get a single peer group by ID."""
    result = await db.execute(
        select(PeerGroup)
        .where(PeerGroup.id == peer_group_id)
        .options(
            selectinload(PeerGroup.tags),
            selectinload(PeerGroup.autonomous_system),
            selectinload(PeerGroup.import_policy),
            selectinload(PeerGroup.export_policy),
        )
    )
    peer_group = result.scalar_one_or_none()

    if peer_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer Group with ID {peer_group_id} not found",
        )

    return PeerGroupResponse(**serialize_peer_group(peer_group))


@router.post("/", response_model=PeerGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_peer_group(
    peer_group_data: PeerGroupCreate,
    db: DbSession,
    user: CurrentUser,
) -> PeerGroupResponse:
    """Create a new peer group."""
    # Check if peer group with same name exists
    result = await db.execute(select(PeerGroup).where(PeerGroup.name == peer_group_data.name))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Peer Group with name '{peer_group_data.name}' already exists",
        )

    peer_group = PeerGroup(**peer_group_data.model_dump())
    db.add(peer_group)
    try:
        await db.commit()
        await db.refresh(peer_group)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create peer group: {str(e)}",
        ) from e

    return PeerGroupResponse(**serialize_peer_group(peer_group))


@router.put("/{peer_group_id}", response_model=PeerGroupResponse)
async def update_peer_group(
    peer_group_id: int,
    peer_group_data: PeerGroupUpdate,
    db: DbSession,
    user: CurrentUser,
) -> PeerGroupResponse:
    """Update an existing peer group."""
    result = await db.execute(
        select(PeerGroup)
        .where(PeerGroup.id == peer_group_id)
        .options(
            selectinload(PeerGroup.tags),
            selectinload(PeerGroup.autonomous_system),
            selectinload(PeerGroup.import_policy),
            selectinload(PeerGroup.export_policy),
        )
    )
    peer_group = result.scalar_one_or_none()

    if peer_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer Group with ID {peer_group_id} not found",
        )

    update_data = peer_group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(peer_group, field, value)

    peer_group.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(peer_group)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update peer group: {str(e)}",
        ) from e

    return PeerGroupResponse(**serialize_peer_group(peer_group))


@router.delete("/{peer_group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_peer_group(
    peer_group_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Delete a peer group."""
    result = await db.execute(select(PeerGroup).where(PeerGroup.id == peer_group_id))
    peer_group = result.scalar_one_or_none()

    if peer_group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer Group with ID {peer_group_id} not found",
        )

    try:
        await db.delete(peer_group)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete peer group: {str(e)}",
        ) from e

    return None

