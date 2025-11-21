"""
Autonomous System CRUD API endpoints.
"""
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from models.entities import AutonomousSystem, Tag
from schemas.entities import (
    AutonomousSystemCreate,
    AutonomousSystemResponse,
    AutonomousSystemUpdate,
    TagResponse,
)

router = APIRouter(prefix="/autonomous-systems", tags=["Autonomous Systems"])


def serialize_as(as_obj: AutonomousSystem) -> dict[str, Any]:
    """Convert SQLAlchemy model to response dict."""
    return {
        "id": as_obj.id,
        "asn": as_obj.asn,
        "description": as_obj.description,
        "status": as_obj.status,
        "rir": as_obj.rir,
        "created_at": as_obj.created_at,
        "updated_at": as_obj.updated_at,
        "tags": [TagResponse.model_validate(tag) for tag in (as_obj.tags or [])],
    }


@router.get("/", response_model=list[AutonomousSystemResponse])
async def list_autonomous_systems(
    db: DbSession,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[AutonomousSystemResponse]:
    """List all autonomous systems with pagination."""
    result = await db.execute(
        select(AutonomousSystem)
        .options(selectinload(AutonomousSystem.tags))
        .offset(skip)
        .limit(limit)
        .order_by(AutonomousSystem.asn)
    )
    as_list = result.scalars().all()
    return [AutonomousSystemResponse(**serialize_as(as_obj)) for as_obj in as_list]


@router.get("/{as_id}", response_model=AutonomousSystemResponse)
async def get_autonomous_system(
    as_id: int,
    db: DbSession,
    user: CurrentUser,
) -> AutonomousSystemResponse:
    """Get a single autonomous system by ID."""
    result = await db.execute(
        select(AutonomousSystem)
        .where(AutonomousSystem.id == as_id)
        .options(selectinload(AutonomousSystem.tags))
    )
    as_obj = result.scalar_one_or_none()

    if as_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Autonomous System with ID {as_id} not found",
        )

    return AutonomousSystemResponse(**serialize_as(as_obj))


@router.post("/", response_model=AutonomousSystemResponse, status_code=status.HTTP_201_CREATED)
async def create_autonomous_system(
    as_data: AutonomousSystemCreate,
    db: DbSession,
    user: CurrentUser,
) -> AutonomousSystemResponse:
    """Create a new autonomous system."""
    # Check if ASN already exists
    result = await db.execute(select(AutonomousSystem).where(AutonomousSystem.asn == as_data.asn))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Autonomous System with ASN {as_data.asn} already exists",
        )

    as_obj = AutonomousSystem(**as_data.model_dump())
    db.add(as_obj)
    try:
        await db.commit()
        await db.refresh(as_obj)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create autonomous system: {str(e)}",
        ) from e

    return AutonomousSystemResponse(**serialize_as(as_obj))


@router.put("/{as_id}", response_model=AutonomousSystemResponse)
async def update_autonomous_system(
    as_id: int,
    as_data: AutonomousSystemUpdate,
    db: DbSession,
    user: CurrentUser,
) -> AutonomousSystemResponse:
    """Update an existing autonomous system."""
    result = await db.execute(
        select(AutonomousSystem)
        .where(AutonomousSystem.id == as_id)
        .options(selectinload(AutonomousSystem.tags))
    )
    as_obj = result.scalar_one_or_none()

    if as_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Autonomous System with ID {as_id} not found",
        )

    update_data = as_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(as_obj, field, value)

    as_obj.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(as_obj)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update autonomous system: {str(e)}",
        ) from e

    return AutonomousSystemResponse(**serialize_as(as_obj))


@router.delete("/{as_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_autonomous_system(
    as_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Delete an autonomous system."""
    result = await db.execute(select(AutonomousSystem).where(AutonomousSystem.id == as_id))
    as_obj = result.scalar_one_or_none()

    if as_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Autonomous System with ID {as_id} not found",
        )

    try:
        await db.delete(as_obj)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete autonomous system: {str(e)}",
        ) from e

    return None

