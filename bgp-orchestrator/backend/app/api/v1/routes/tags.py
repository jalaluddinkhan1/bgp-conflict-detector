"""
Tag CRUD API endpoints.
"""
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import CurrentUser, DbSession
from models.entities import Tag
from schemas.entities import TagCreate, TagResponse, TagUpdate

router = APIRouter(prefix="/tags", tags=["Tags"])


@router.get("/", response_model=list[TagResponse])
async def list_tags(
    db: DbSession,
    user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[TagResponse]:
    """List all tags with pagination."""
    result = await db.execute(select(Tag).offset(skip).limit(limit).order_by(Tag.name))
    tags = result.scalars().all()
    return [TagResponse.model_validate(tag) for tag in tags]


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    db: DbSession,
    user: CurrentUser,
) -> TagResponse:
    """Get a single tag by ID."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag with ID {tag_id} not found",
        )

    return TagResponse.model_validate(tag)


@router.post("/", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_data: TagCreate,
    db: DbSession,
    user: CurrentUser,
) -> TagResponse:
    """Create a new tag."""
    # Generate slug if not provided
    if not tag_data.slug:
        tag_data.slug = tag_data.name.lower().replace(" ", "-").replace("_", "-")
        tag_data.slug = "".join(c if c.isalnum() or c == "-" else "" for c in tag_data.slug)

    # Check if tag with same name or slug exists
    result = await db.execute(
        select(Tag).where((Tag.name == tag_data.name) | (Tag.slug == tag_data.slug))
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag with name '{tag_data.name}' or slug '{tag_data.slug}' already exists",
        )

    tag = Tag(**tag_data.model_dump())
    db.add(tag)
    try:
        await db.commit()
        await db.refresh(tag)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tag: {str(e)}",
        ) from e

    return TagResponse.model_validate(tag)


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_data: TagUpdate,
    db: DbSession,
    user: CurrentUser,
) -> TagResponse:
    """Update an existing tag."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag with ID {tag_id} not found",
        )

    update_data = tag_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(tag, field, value)

    tag.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(tag)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tag: {str(e)}",
        ) from e

    return TagResponse.model_validate(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: int,
    db: DbSession,
    user: CurrentUser,
) -> None:
    """Delete a tag."""
    result = await db.execute(select(Tag).where(Tag.id == tag_id))
    tag = result.scalar_one_or_none()

    if tag is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tag with ID {tag_id} not found",
        )

    try:
        await db.delete(tag)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tag: {str(e)}",
        ) from e

    return None

