"""
Peer Endpoint CRUD API endpoints.
"""
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from models.entities import PeerEndpoint
from schemas.entities import (
    PeerEndpointCreate,
    PeerEndpointResponse,
    PeerEndpointUpdate,
    TagResponse,
)

router = APIRouter(prefix="/peer-endpoints", tags=["Peer Endpoints"])


def serialize_peer_endpoint(pe: PeerEndpoint) -> dict[str, Any]:
    """Convert SQLAlchemy model to response dict."""
    return {
        "id": pe.id,
        "name": pe.name,
        "device_id": pe.device_id,
        "routing_instance_id": pe.routing_instance_id,
        "peer_group_id": pe.peer_group_id,
        "source_ip_address": str(pe.source_ip_address),
        "source_interface": pe.source_interface,
        "description": pe.description,
        "enabled": pe.enabled,
        "autonomous_system_id": pe.autonomous_system_id,
        "import_policy_id": pe.import_policy_id,
        "export_policy_id": pe.export_policy_id,
        "hold_time": pe.hold_time,
        "keepalive": pe.keepalive,
        "remote_endpoint_id": pe.remote_endpoint_id,
        "created_at": pe.created_at,
        "updated_at": pe.updated_at,
        "tags": [TagResponse.model_validate(tag) for tag in (pe.tags or [])],
        "autonomous_system": {
            "id": pe.autonomous_system.id,
            "asn": pe.autonomous_system.asn,
            "description": pe.autonomous_system.description,
            "status": pe.autonomous_system.status,
        } if pe.autonomous_system else None,
        "import_policy": {
            "id": pe.import_policy.id,
            "name": pe.import_policy.name,
            "type": pe.import_policy.type,
        } if pe.import_policy else None,
        "export_policy": {
            "id": pe.export_policy.id,
            "name": pe.export_policy.name,
            "type": pe.export_policy.type,
        } if pe.export_policy else None,
    }


@router.get("/", response_model=list[PeerEndpointResponse])
async def list_peer_endpoints(
    db: DbSession,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    device_id: int | None = Query(None),
) -> list[PeerEndpointResponse]:
    """List all peer endpoints with pagination."""
    query = select(PeerEndpoint).options(
        selectinload(PeerEndpoint.tags),
        selectinload(PeerEndpoint.autonomous_system),
        selectinload(PeerEndpoint.import_policy),
        selectinload(PeerEndpoint.export_policy),
    )
    
    if device_id:
        query = query.where(PeerEndpoint.device_id == device_id)
    
    query = query.offset(skip).limit(limit).order_by(PeerEndpoint.name)
    
    result = await db.execute(query)
    peer_endpoints = result.scalars().all()
    return [PeerEndpointResponse(**serialize_peer_endpoint(pe)) for pe in peer_endpoints]


@router.get("/{peer_endpoint_id}", response_model=PeerEndpointResponse)
async def get_peer_endpoint(
    peer_endpoint_id: int,
    db: DbSession,
    user: CurrentUser,
) -> PeerEndpointResponse:
    """Get a single peer endpoint by ID."""
    result = await db.execute(
        select(PeerEndpoint)
        .where(PeerEndpoint.id == peer_endpoint_id)
        .options(
            selectinload(PeerEndpoint.tags),
            selectinload(PeerEndpoint.autonomous_system),
            selectinload(PeerEndpoint.import_policy),
            selectinload(PeerEndpoint.export_policy),
        )
    )
    peer_endpoint = result.scalar_one_or_none()

    if peer_endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer Endpoint with ID {peer_endpoint_id} not found",
        )

    return PeerEndpointResponse(**serialize_peer_endpoint(peer_endpoint))


@router.post("/", response_model=PeerEndpointResponse, status_code=status.HTTP_201_CREATED)
async def create_peer_endpoint(
    peer_endpoint_data: PeerEndpointCreate,
    db: DbSession,
    user: CurrentUser,
) -> PeerEndpointResponse:
    """Create a new peer endpoint."""
    peer_endpoint = PeerEndpoint(
        **peer_endpoint_data.model_dump(),
        source_ip_address=str(peer_endpoint_data.source_ip_address),
    )
    db.add(peer_endpoint)
    try:
        await db.commit()
        await db.refresh(peer_endpoint)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create peer endpoint: {str(e)}",
        ) from e

    return PeerEndpointResponse(**serialize_peer_endpoint(peer_endpoint))


@router.put("/{peer_endpoint_id}", response_model=PeerEndpointResponse)
async def update_peer_endpoint(
    peer_endpoint_id: int,
    peer_endpoint_data: PeerEndpointUpdate,
    db: DbSession,
    user: CurrentUser,
) -> PeerEndpointResponse:
    """Update an existing peer endpoint."""
    result = await db.execute(
        select(PeerEndpoint)
        .where(PeerEndpoint.id == peer_endpoint_id)
        .options(
            selectinload(PeerEndpoint.tags),
            selectinload(PeerEndpoint.autonomous_system),
            selectinload(PeerEndpoint.import_policy),
            selectinload(PeerEndpoint.export_policy),
        )
    )
    peer_endpoint = result.scalar_one_or_none()

    if peer_endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer Endpoint with ID {peer_endpoint_id} not found",
        )

    update_data = peer_endpoint_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            if field == "source_ip_address":
                setattr(peer_endpoint, field, str(value))
            else:
                setattr(peer_endpoint, field, value)

    peer_endpoint.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(peer_endpoint)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update peer endpoint: {str(e)}",
        ) from e

    return PeerEndpointResponse(**serialize_peer_endpoint(peer_endpoint))


@router.delete("/{peer_endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_peer_endpoint(
    peer_endpoint_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Delete a peer endpoint."""
    result = await db.execute(select(PeerEndpoint).where(PeerEndpoint.id == peer_endpoint_id))
    peer_endpoint = result.scalar_one_or_none()

    if peer_endpoint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Peer Endpoint with ID {peer_endpoint_id} not found",
        )

    try:
        await db.delete(peer_endpoint)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete peer endpoint: {str(e)}",
        ) from e

    return None

