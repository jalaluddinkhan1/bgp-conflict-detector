"""
FastAPI application factory with middleware and routing.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.routes import anomalies, bgp_peerings, customer, features, ml
from app.config import settings
from app.dependencies import get_db_engine, get_redis
from app.middleware.logging import RequestLoggingMiddleware, configure_structlog, logger
from observability.metrics import metrics_router
from observability.pyroscope_integration import start_pyroscope_profiling
from observability.victoriametrics_integration import start_background_forwarder, stop_background_forwarder

# Configure structured logging
configure_structlog()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    - Connect to database on startup
    - Connect to Redis on startup
    - Cleanup on shutdown
    """
    # Startup
    logger.info("Starting BGP Orchestrator API")

    # Initialize database connection pool
    engine = get_db_engine()
    logger.info("Database engine initialized")

    # Test Redis connection
    try:
        redis_client = get_redis()
        redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
    
    # Start VictoriaMetrics forwarder if enabled
    if settings.VICTORIAMETRICS_ENABLED:
        start_background_forwarder(interval_seconds=60)
        logger.info("VictoriaMetrics forwarder started")
    
    # Start Pyroscope profiling if enabled
    start_pyroscope_profiling()
    
    # Start Kafka consumer if enabled
    if settings.KAFKA_ENABLED:
        from streaming.bgp_consumer import start_kafka_consumer
        await start_kafka_consumer()
        logger.info("Kafka consumer started")
    
    # Start feature store materialization if enabled
    if settings.FEATURE_STORE_ENABLED:
        from streaming.materialization_job import start_background_materialization
        start_background_materialization(interval_minutes=5)
        logger.info("Feature store materialization scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down BGP Orchestrator API")
    
    # Stop VictoriaMetrics forwarder
    if settings.VICTORIAMETRICS_ENABLED:
        stop_background_forwarder()
    
    # Stop feature store materialization
    if settings.FEATURE_STORE_ENABLED:
        from streaming.materialization_job import stop_background_materialization
        stop_background_materialization()
    
    # Close database connections
    await engine.dispose()
    logger.info("Database connections closed")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI app instance
    """
    app = FastAPI(
        title="BGP Orchestrator API",
        description="Enterprise BGP network orchestration and conflict detection API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        responses={
            401: {"description": "Unauthorized"},
            403: {"description": "Forbidden"},
            404: {"description": "Not found"},
            429: {"description": "Rate limit exceeded"},
        },
    )

    # Add rate limiting middleware (must be before other middleware)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add request logging middleware
    app.add_middleware(RequestLoggingMiddleware)

    # Register routers
    app.include_router(
        bgp_peerings.router,
        prefix="/api/v1",
        tags=["BGP Peerings"],
    )
    
    # Register ML router
    app.include_router(
        ml.router,
        prefix="/api/v1",
    )
    
    # Register anomalies router
    app.include_router(
        anomalies.router,
        prefix="/api/v1",
    )
    
    # Register features router
    app.include_router(
        features.router,
        prefix="/api/v1",
    )
    
    # Register customer portal router
    app.include_router(
        customer.router,
        prefix="/api/v1",
    )

    # Register metrics router
    app.include_router(metrics_router)

    # Health check endpoints
    @app.get(
        "/healthz",
        status_code=status.HTTP_200_OK,
        tags=["Health"],
        summary="Health check endpoint",
        description="Returns 200 if the service is healthy",
    )
    async def healthz() -> dict[str, str]:
        """Health check endpoint (Kubernetes liveness probe)."""
        return {"status": "healthy"}

    @app.get(
        "/readyz",
        status_code=status.HTTP_200_OK,
        tags=["Health"],
        summary="Readiness check endpoint",
        description="Returns 200 if the service is ready to accept traffic",
    )
    async def readyz() -> dict[str, str]:
        """Readiness check endpoint (Kubernetes readiness probe)."""
        # Check database connection
        try:
            from sqlalchemy import text
            engine = get_db_engine()
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not ready", "error": str(e)},
            )

        # Check Redis connection
        try:
            redis_client = get_redis()
            redis_client.ping()
        except Exception:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not ready", "error": "Redis unavailable"},
            )

        return {"status": "ready"}

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "body": exc.body,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions."""
        logger.error("Unhandled exception", exc_info=exc, path=request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    return app


# Create application instance
app = create_application()


# Rate limit decorator for routes (10 requests per second per user)
def rate_limit_per_user():
    """Rate limit: 10 requests per second per user."""
    return limiter.limit("10/second")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )

