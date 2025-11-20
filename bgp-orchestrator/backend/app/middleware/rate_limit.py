"""
Redis-based rate limiting middleware.
"""
import time
from typing import Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.dependencies import get_redis
from redis import Redis


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis sorted sets."""

    def __init__(
        self,
        app: ASGIApp,
        redis_client: Redis | None = None,
        requests_per_minute: int = 60,
        exclude_paths: list[str] | None = None,
    ):
        """
        Initialize rate limiter middleware.

        Args:
            app: ASGI application
            redis_client: Redis client instance (optional, will get from dependencies if None)
            requests_per_minute: Maximum requests per minute per IP
            exclude_paths: List of paths to exclude from rate limiting
        """
        super().__init__(app)
        self.redis_client = redis_client
        self.requests_per_minute = requests_per_minute
        self.exclude_paths = exclude_paths or [
            "/healthz",
            "/readyz",
            "/livez",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request with rate limiting.

        Args:
            request: FastAPI/Starlette request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get Redis client
        if self.redis_client is None:
            self.redis_client = get_redis()

        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Rate limit key
        key = f"rate_limit:{client_ip}"
        now = time.time()

        try:
            # Use Redis pipeline for atomic operations
            # Note: Redis client from dependencies is synchronous, so we use it directly
            pipe = self.redis_client.pipeline()

            # Remove old requests (older than 60 seconds)
            pipe.zremrangebyscore(key, 0, now - 60)

            # Add current request with timestamp as score
            pipe.zadd(key, {str(now): now})

            # Count requests in last minute
            pipe.zcard(key)

            # Set expiration on key (cleanup after 60 seconds)
            pipe.expire(key, 60)

            # Execute pipeline (synchronous Redis)
            results = pipe.execute()
            request_count = results[2]

            # Check if rate limit exceeded
            if request_count > self.requests_per_minute:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute",
                    headers={
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "Retry-After": "60",
                    },
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            remaining = max(0, self.requests_per_minute - request_count)
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(now + 60))

            return response

        except HTTPException:
            raise
        except Exception as e:
            # If Redis fails, log but don't block requests
            # In production, you might want to fail closed
            print(f"Rate limiting error: {e}")
            return await call_next(request)

