"""
Structured logging middleware with request ID generation.
"""
import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


def configure_structlog() -> None:
    """Configure structlog with JSON format."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level="INFO"),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# Configure structlog on module import
configure_structlog()

# Get logger
logger = structlog.get_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with structured logging."""

    def __init__(self, app: ASGIApp, exclude_paths: list[str] | None = None):
        """
        Initialize request logging middleware.

        Args:
            app: ASGI application
            exclude_paths: List of paths to exclude from logging (e.g., health checks)
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/openapi.json", "/redoc"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: FastAPI/Starlette request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Generate request ID
        request_id = str(uuid.uuid4())

        # Add request ID to request state
        request.state.request_id = request_id

        # Add request ID to context for structured logging
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Check if path should be excluded
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            response = await call_next(request)
            return response

        # Extract user information if available
        user_id = None
        user_email = None
        if hasattr(request.state, "user"):
            user_id = getattr(request.state.user, "id", None)
            user_email = getattr(request.state.user, "email", None)

        # Log request start
        start_time = time.time()
        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query_params=dict(request.query_params),
            client_host=request.client.host if request.client else None,
            user_id=user_id,
            user_email=user_email,
            user_agent=request.headers.get("user-agent"),
        )

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            duration = time.time() - start_time

            # Log successful response
            logger.info(
                "request_completed",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round(duration * 1000, 2),
                user_id=user_id,
                user_email=user_email,
            )

        except Exception as e:
            duration = time.time() - start_time
            # Log error
            logger.error(
                "request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
                user_id=user_id,
                user_email=user_email,
                exc_info=True,
            )
            raise

        finally:
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

        return response


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def bind_user_context(user_id: str | None = None, user_email: str | None = None) -> None:
    """Bind user context to structured logging."""
    structlog.contextvars.bind_contextvars(user_id=user_id, user_email=user_email)


def clear_logging_context() -> None:
    """Clear logging context variables."""
    structlog.contextvars.clear_contextvars()

