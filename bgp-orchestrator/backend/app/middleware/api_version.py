"""
API versioning middleware to enforce version headers.
"""
from fastapi import Header, HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate API version headers.
    
    Requires X-API-Version header for all /api/v1/* endpoints.
    """

    def __init__(self, app: ASGIApp, required_version: str = "1.0"):
        """
        Initialize API version middleware.

        Args:
            app: ASGI application
            required_version: Required API version (default: "1.0")
        """
        super().__init__(app)
        self.required_version = required_version

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request with API version validation.

        Args:
            request: FastAPI/Starlette request
            call_next: Next middleware/handler

        Returns:
            Response
        """
        # Skip version check for non-API endpoints
        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        # Skip version check for docs and health endpoints
        excluded_paths = ["/api/v1/docs", "/api/v1/redoc", "/api/v1/openapi.json", "/api/v1/health"]
        if any(request.url.path.startswith(path) for path in excluded_paths):
            return await call_next(request)

        # Check for X-API-Version header
        api_version = request.headers.get("X-API-Version")
        
        if not api_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required header: X-API-Version",
                headers={"X-API-Version": self.required_version},
            )

        # Validate version format (semver: major.minor)
        import re
        if not re.match(r"^1\.[0-9]+$", api_version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API version format. Expected: 1.x, got: {api_version}",
                headers={"X-API-Version": self.required_version},
            )

        # Check if version is supported
        if api_version != self.required_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API version {api_version} not supported. Supported version: {self.required_version}",
                headers={"X-API-Version": self.required_version},
            )

        # Add version to request state for use in routes
        request.state.api_version = api_version

        response = await call_next(request)
        
        # Add version header to response
        response.headers["X-API-Version"] = self.required_version
        
        return response

