"""
Authentication and authorization module.
Supports OAuth2 providers (Azure AD, Google, Okta) and local JWT authentication.
"""
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import OAuth2Provider, settings


class UserRole(str, Enum):
    """User role definitions."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"


class TokenType(str, Enum):
    """JWT token types."""

    ACCESS = "access"
    REFRESH = "refresh"


class Token(BaseModel):
    """JWT token response model."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Decoded token data."""

    user_id: str
    email: str
    roles: list[str]
    provider: str | None = None


class User(BaseModel):
    """User model."""

    id: str
    email: str
    roles: list[UserRole]
    provider: OAuth2Provider | None = None
    is_active: bool = True


class PasswordHash:
    """Password hashing utilities using bcrypt."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash."""
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )


class OAuth2ProviderHandler:
    """Base class for OAuth2 provider implementations."""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str | None = None):
        """Initialize OAuth2 provider."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from provider."""
        raise NotImplementedError("Subclasses must implement get_user_info")

    async def validate_token(self, token: str) -> bool:
        """Validate token with provider."""
        raise NotImplementedError("Subclasses must implement validate_token")


class AzureADHandler(OAuth2ProviderHandler):
    """Azure AD OAuth2 provider handler."""

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Azure AD."""
        # TODO: Implement Azure AD user info endpoint
        # Example: GET https://graph.microsoft.com/v1.0/me
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://graph.microsoft.com/v1.0/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def validate_token(self, token: str) -> bool:
        """Validate Azure AD token."""
        # TODO: Implement token validation with Azure AD
        return True


class GoogleHandler(OAuth2ProviderHandler):
    """Google OAuth2 provider handler."""

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Google."""
        # TODO: Implement Google user info endpoint
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def validate_token(self, token: str) -> bool:
        """Validate Google token."""
        # TODO: Implement token validation with Google
        return True


class OktaHandler(OAuth2ProviderHandler):
    """Okta OAuth2 provider handler."""

    def __init__(self, client_id: str, client_secret: str, tenant_id: str | None = None, okta_domain: str = ""):
        """Initialize Okta handler with domain."""
        super().__init__(client_id, client_secret, tenant_id)
        self.okta_domain = okta_domain

    async def get_user_info(self, access_token: str) -> dict[str, Any]:
        """Get user information from Okta."""
        # TODO: Implement Okta user info endpoint
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{self.okta_domain}/oauth2/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def validate_token(self, token: str) -> bool:
        """Validate Okta token."""
        # TODO: Implement token validation with Okta
        return True


class JWTManager:
    """JWT token creation and validation."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """Initialize JWT manager."""
        self.secret_key = secret_key
        self.algorithm = algorithm

    def create_access_token(self, data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

        to_encode.update({"exp": expire, "type": TokenType.ACCESS.value})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def create_refresh_token(self, data: dict[str, Any]) -> str:
        """Create a JWT refresh token."""
        to_encode = data.copy()
        # Refresh tokens last 7 days
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        to_encode.update({"exp": expire, "type": TokenType.REFRESH.value})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication credentials: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def create_token_pair(self, user_id: str, email: str, roles: list[str], provider: str | None = None) -> Token:
        """Create both access and refresh tokens."""
        token_data = {
            "sub": user_id,
            "email": email,
            "roles": roles,
            "provider": provider or "local",
        }

        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_EXPIRATION_HOURS * 3600,
        )

    def refresh_access_token(self, refresh_token: str) -> str:
        """Create a new access token from a refresh token."""
        payload = self.decode_token(refresh_token)
        if payload.get("type") != TokenType.REFRESH.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )

        # Create new access token with same user data
        token_data = {
            "sub": payload["sub"],
            "email": payload["email"],
            "roles": payload.get("roles", []),
            "provider": payload.get("provider"),
        }
        return self.create_access_token(token_data)


# Global JWT manager instance
jwt_manager = JWTManager(secret_key=settings.jwt_secret, algorithm=settings.ALGORITHM)

# Security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            ...
    """
    token = credentials.credentials
    payload = jwt_manager.decode_token(token)

    # Verify token type
    if payload.get("type") != TokenType.ACCESS.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    email = payload.get("email")
    roles = payload.get("roles", [])
    provider = payload.get("provider")

    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return User(
        id=user_id,
        email=email,
        roles=[UserRole(role) for role in roles if role in [r.value for r in UserRole]],
        provider=OAuth2Provider(provider) if provider and provider in [p.value for p in OAuth2Provider] else None,
    )


def require_role(*allowed_roles: UserRole):
    """
    Decorator to require specific roles for access.

    Usage:
        @app.get("/admin")
        @require_role(UserRole.ADMIN)
        async def admin_route(user: User = Depends(get_current_user)):
            ...
    """
    allowed_role_values = {role.value for role in allowed_roles}

    def role_checker(user: User = Depends(get_current_user)) -> User:
        user_roles = {role.value for role in user.roles}
        if not user_roles.intersection(allowed_role_values):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(allowed_role_values)}",
            )
        return user

    return role_checker


async def get_oauth2_handler(provider: OAuth2Provider) -> OAuth2ProviderHandler | None:
    """Get OAuth2 handler for a specific provider."""
    if not settings.OAUTH2_PROVIDER or settings.OAUTH2_PROVIDER != provider:
        return None

    if provider == OAuth2Provider.AZURE:
        if not settings.OAUTH2_CLIENT_ID or not settings.OAUTH2_CLIENT_SECRET:
            return None
        return AzureADHandler(
            client_id=settings.OAUTH2_CLIENT_ID,
            client_secret=settings.OAUTH2_CLIENT_SECRET,
            tenant_id=settings.OAUTH2_TENANT_ID,
        )
    elif provider == OAuth2Provider.GOOGLE:
        if not settings.OAUTH2_CLIENT_ID or not settings.OAUTH2_CLIENT_SECRET:
            return None
        return GoogleHandler(
            client_id=settings.OAUTH2_CLIENT_ID,
            client_secret=settings.OAUTH2_CLIENT_SECRET,
        )
    elif provider == OAuth2Provider.OKTA:
        if not settings.OAUTH2_CLIENT_ID or not settings.OAUTH2_CLIENT_SECRET:
            return None
        # Okta domain would need to be in settings
        return OktaHandler(
            client_id=settings.OAUTH2_CLIENT_ID,
            client_secret=settings.OAUTH2_CLIENT_SECRET,
            okta_domain=settings.OAUTH2_TENANT_ID or "",
        )

    return None

