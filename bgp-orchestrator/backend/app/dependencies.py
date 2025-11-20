"""
FastAPI dependencies for database, Redis, authentication, and external services.
"""
from functools import lru_cache
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from app.config import settings
from core.conflict_detector import BGPConflictDetector
from security.auth import User, get_current_user as auth_get_current_user, require_role as auth_require_role, UserRole


# Database Engine and Session Factory
_engine = None
_async_session_factory = None


def get_db_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        # Convert postgresql:// to postgresql+asyncpg:// for async support
        database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        _engine = create_async_engine(
            database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=False,
        )
    return _engine


def get_async_session_factory():
    """Get or create async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_db_engine()
        _async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Usage:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Redis Client
_redis_client: Redis | None = None


@lru_cache()
def get_redis() -> Redis:
    """
    Get Redis client instance (singleton).

    Usage:
        @app.get("/cache")
        async def get_cache(redis: Redis = Depends(get_redis)):
            ...
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
        )
    return _redis_client


# Current User Dependency
async def get_current_user(user: User = Depends(auth_get_current_user)) -> User:
    """
    Get current authenticated user (wrapper for consistency).

    Usage:
        @app.get("/profile")
        async def get_profile(user: User = Depends(get_current_user)):
            ...
    """
    return user


def require_role(*roles: UserRole):
    """
    Dependency factory to require specific roles.

    Usage:
        @app.delete("/admin/delete")
        @require_role(UserRole.ADMIN)
        async def admin_delete(user: User = Depends(get_current_user)):
            ...
    """
    return auth_require_role(*roles)


# Conflict Detector
_conflict_detector: BGPConflictDetector | None = None


@lru_cache()
def get_conflict_detector() -> BGPConflictDetector:
    """
    Get BGP conflict detector instance (singleton).

    Usage:
        @app.post("/peerings")
        async def create_peering(detector: BGPConflictDetector = Depends(get_conflict_detector)):
            ...
    """
    global _conflict_detector
    if _conflict_detector is None:
        _conflict_detector = BGPConflictDetector()
    return _conflict_detector


# Import real service clients
from services.batfish_client import BatfishClient
from services.suzieq_client import SuzieQClient
from services.ripe_ris_client import RIPEClient


# Batfish Client
_batfish_client: BatfishClient | None = None


@lru_cache()
def get_batfish_client() -> BatfishClient | None:
    """
    Get Batfish client instance (singleton).

    Usage:
        @app.post("/validate")
        async def validate(client: BatfishClient = Depends(get_batfish_client)):
            ...
    """
    global _batfish_client
    if _batfish_client is None and settings.BATFISH_ENDPOINT:
        _batfish_client = BatfishClient()
    return _batfish_client


# SuzieQ Client
_suzieq_client: SuzieQClient | None = None


@lru_cache()
def get_suzieq_client() -> SuzieQClient | None:
    """
    Get SuzieQ client instance (singleton).

    Usage:
        @app.get("/devices")
        async def get_devices(client: SuzieQClient = Depends(get_suzieq_client)):
            ...
    """
    global _suzieq_client
    if _suzieq_client is None and settings.SUZIEQ_ENDPOINT:
        _suzieq_client = SuzieQClient()
    return _suzieq_client


# RIPE RIS Client
_ripe_ris_client: RIPEClient | None = None


@lru_cache()
def get_ripe_ris_client() -> RIPEClient | None:
    """
    Get RIPE RIS client instance (singleton).

    Usage:
        @app.get("/bgp-updates")
        async def get_updates(client: RIPEClient = Depends(get_ripe_ris_client)):
            ...
    """
    global _ripe_ris_client
    if _ripe_ris_client is None and settings.RIPE_RIS_ENABLED:
        redis_client = get_redis()
        _ripe_ris_client = RIPEClient(redis_client=redis_client)
    return _ripe_ris_client


# Async dependencies type hints
DbSession = Annotated[AsyncSession, Depends(get_db)]
RedisClient = Annotated[Redis, Depends(get_redis)]
CurrentUser = Annotated[User, Depends(get_current_user)]
ConflictDetector = Annotated[BGPConflictDetector, Depends(get_conflict_detector)]
BatfishClientDep = Annotated[BatfishClient | None, Depends(get_batfish_client)]
SuzieQClientDep = Annotated[SuzieQClient | None, Depends(get_suzieq_client)]
RIPEClientDep = Annotated[RIPEClient | None, Depends(get_ripe_ris_client)]

