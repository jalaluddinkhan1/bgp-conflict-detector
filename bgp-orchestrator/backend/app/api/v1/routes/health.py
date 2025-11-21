"""
Health check endpoints for Kubernetes and monitoring.
"""
import time
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import DbSession, RedisClient, get_db_engine, CurrentUser
from app.config import settings
from security.auth import require_role, UserRole

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    """
    Public health check endpoint - minimal information for Kubernetes probes.
    
    Does not expose sensitive metrics or detailed diagnostics.
    """
    return {"status": "healthy"}


@router.get("/healthz/internal", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def healthz_internal(
    db: DbSession,
    redis: RedisClient,
    user: CurrentUser,
) -> dict[str, Any]:
    """
    Internal health check with detailed diagnostics - requires admin authentication.
    
    Returns:
        Health status with detailed checks including latency metrics
    """
    checks: dict[str, Any] = {}

    # Check database
    try:
        start = time.time()
        await db.execute("SELECT 1")
        checks["database"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Check Redis
    try:
        start = time.time()
        redis.ping()
        checks["redis"] = {
            "status": "healthy",
            "latency_ms": round((time.time() - start) * 1000, 2),
        }
    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "error": str(e),
        }

    # Check external services
    if settings.BATFISH_ENDPOINT:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start = time.time()
                response = await client.get(f"{settings.BATFISH_ENDPOINT}/health")
                checks["batfish"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "latency_ms": round((time.time() - start) * 1000, 2),
                }
        except Exception as e:
            checks["batfish"] = {
                "status": "unhealthy",
                "error": str(e),
            }

    if settings.SUZIEQ_ENDPOINT:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                start = time.time()
                response = await client.get(f"{settings.SUZIEQ_ENDPOINT}/health")
                checks["suzieq"] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "latency_ms": round((time.time() - start) * 1000, 2),
                }
        except Exception as e:
            checks["suzieq"] = {
                "status": "unhealthy",
                "error": str(e),
            }

    # Overall status
    is_healthy = all(
        check.get("status") == "healthy" for check in checks.values() if isinstance(check, dict)
    )

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "checks": checks,
        "version": "1.0.0",
    }


@router.get("/readyz")
async def readyz() -> dict[str, str]:
    """
    Kubernetes readiness check - indicates if the service is ready to accept traffic.

    Returns:
        Ready status
    """
    return {"status": "ready"}


@router.get("/livez")
async def livez() -> dict[str, str]:
    """
    Kubernetes liveness check - indicates if the service is alive.

    Returns:
        Alive status
    """
    return {"status": "alive"}

