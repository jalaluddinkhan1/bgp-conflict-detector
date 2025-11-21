"""
OAuth2 authentication routes with CSRF protection via state parameter validation.
"""
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from redis import Redis

from app.config import OAuth2Provider, settings
from app.dependencies import RedisClient
from security.auth import OAuth2ProviderHandler, get_oauth2_handler, jwt_manager

router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 provider configuration URLs
OAUTH2_CONFIGS = {
    OAuth2Provider.AZURE: {
        "authorize_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
        "token_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
    },
    OAuth2Provider.GOOGLE: {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
    },
    OAuth2Provider.OKTA: {
        "authorize_url": "https://{okta_domain}/oauth2/v1/authorize",
        "token_url": "https://{okta_domain}/oauth2/v1/token",
    },
}


def get_oauth2_authorize_url(provider: OAuth2Provider, state: str, redirect_uri: str) -> str:
    """Build OAuth2 authorization URL for the provider."""
    if not settings.OAUTH2_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth2 client ID not configured",
        )

    config = OAUTH2_CONFIGS[provider]
    base_url = config["authorize_url"]

    # Replace placeholders in URL
    if provider == OAuth2Provider.AZURE:
        tenant_id = settings.OAUTH2_TENANT_ID or "common"
        base_url = base_url.format(tenant_id=tenant_id)
    elif provider == OAuth2Provider.OKTA:
        okta_domain = settings.OAUTH2_TENANT_ID or ""
        if not okta_domain:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Okta domain (OAUTH2_TENANT_ID) not configured",
            )
        base_url = base_url.format(okta_domain=okta_domain)

    # Build query parameters
    params = {
        "client_id": settings.OAUTH2_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }

    # Provider-specific parameters
    if provider == OAuth2Provider.AZURE:
        params["response_mode"] = "query"
    elif provider == OAuth2Provider.GOOGLE:
        params["access_type"] = "offline"  # Request refresh token
        params["prompt"] = "consent"

    return f"{base_url}?{urlencode(params)}"


async def exchange_code_for_token(
    provider: OAuth2Provider, code: str, redirect_uri: str
) -> dict:
    """Exchange authorization code for access token."""
    if not settings.OAUTH2_CLIENT_ID or not settings.OAUTH2_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth2 credentials not configured",
        )

    config = OAUTH2_CONFIGS[provider]
    token_url = config["token_url"]

    # Replace placeholders in URL
    if provider == OAuth2Provider.AZURE:
        tenant_id = settings.OAUTH2_TENANT_ID or "common"
        token_url = token_url.format(tenant_id=tenant_id)
    elif provider == OAuth2Provider.OKTA:
        okta_domain = settings.OAUTH2_TENANT_ID or ""
        if not okta_domain:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Okta domain not configured",
            )
        token_url = token_url.format(okta_domain=okta_domain)

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        data = {
            "client_id": settings.OAUTH2_CLIENT_ID,
            "client_secret": settings.OAUTH2_CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }

        response = await client.post(token_url, data=data)
        response.raise_for_status()
        return response.json()


@router.get("/login")
async def oauth2_login(
    request: Request,
    provider: str = Query(..., description="OAuth2 provider (azure/google/okta)"),
    state: str | None = Query(None, description="Optional state parameter (auto-generated if not provided)"),
    redis: Redis = Depends(RedisClient),
):
    """
    Initiate OAuth2 login flow with CSRF protection.

    Generates a secure state token and stores it in Redis for validation during callback.
    """
    # Validate provider
    try:
        oauth2_provider = OAuth2Provider(provider.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid OAuth2 provider: {provider}. Supported: azure, google, okta",
        )

    # Check if OAuth2 is configured
    if not settings.OAUTH2_PROVIDER or settings.OAUTH2_PROVIDER != oauth2_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth2 provider {provider} is not configured",
        )

    # Get redirect URI
    redirect_uri = settings.OAUTH2_REDIRECT_URI
    if not redirect_uri:
        # Auto-generate from request if not configured
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/api/v1/auth/callback"

    # Generate state token if not provided (CSRF protection)
    if not state:
        state = secrets.token_urlsafe(32)
        # Store in Redis with 10 minute TTL
        redis.setex(f"oauth_state:{state}", 600, "pending")
    else:
        # Validate existing state token
        state_key = f"oauth_state:{state}"
        stored_state = redis.get(state_key)
        if not stored_state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state parameter",
            )

    # Build authorization URL
    try:
        authorize_url = get_oauth2_authorize_url(oauth2_provider, state, redirect_uri)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build OAuth2 URL: {str(e)}",
        )

    # Redirect to OAuth2 provider
    return RedirectResponse(url=authorize_url)


@router.get("/callback")
async def oauth2_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from OAuth2 provider"),
    state: str = Query(..., description="State parameter for CSRF protection"),
    provider: str | None = Query(None, description="OAuth2 provider (optional, inferred from state)"),
    redis: Redis = Depends(RedisClient),
):
    """
    OAuth2 callback endpoint with state validation.

    Validates the state parameter against Redis to prevent CSRF attacks.
    """
    # Validate state parameter (CRITICAL: CSRF protection)
    state_key = f"oauth_state:{state}"
    stored_state = redis.get(state_key)
    if not stored_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state parameter. Possible CSRF attack.",
        )

    # Delete state token (one-time use)
    redis.delete(state_key)

    # Determine provider
    if provider:
        try:
            oauth2_provider = OAuth2Provider(provider.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OAuth2 provider: {provider}",
            )
    else:
        # Infer from configured provider
        if not settings.OAUTH2_PROVIDER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OAuth2 provider not configured",
            )
        oauth2_provider = settings.OAUTH2_PROVIDER

    # Get redirect URI
    redirect_uri = settings.OAUTH2_REDIRECT_URI
    if not redirect_uri:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/api/v1/auth/callback"

    # Exchange code for access token
    try:
        token_response = await exchange_code_for_token(oauth2_provider, code, redirect_uri)
        access_token = token_response.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received from OAuth2 provider",
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to exchange code for token: {e.response.text}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth2 token exchange failed: {str(e)}",
        )

    # Get OAuth2 handler and fetch user info
    handler = await get_oauth2_handler(oauth2_provider)
    if not handler:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OAuth2 handler not available for {oauth2_provider.value}",
        )

    try:
        user_info = await handler.get_user_info(access_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch user information: {str(e)}",
        )

    # Extract user information (provider-specific)
    if oauth2_provider == OAuth2Provider.AZURE:
        user_id = user_info.get("id")
        email = user_info.get("mail") or user_info.get("userPrincipalName")
        # Default role based on provider or user attributes
        roles = ["viewer"]  # Could be enhanced with Azure AD groups
    elif oauth2_provider == OAuth2Provider.GOOGLE:
        user_id = user_info.get("id")
        email = user_info.get("email")
        roles = ["viewer"]
    elif oauth2_provider == OAuth2Provider.OKTA:
        user_id = user_info.get("sub")
        email = user_info.get("email")
        roles = ["viewer"]
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unsupported OAuth2 provider",
        )

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incomplete user information from OAuth2 provider",
        )

    # Create JWT tokens
    token_pair = jwt_manager.create_token_pair(
        user_id=user_id,
        email=email,
        roles=roles,
        provider=oauth2_provider.value,
    )

    # Return tokens (in production, you might want to redirect to frontend with tokens)
    return {
        "access_token": token_pair.access_token,
        "refresh_token": token_pair.refresh_token,
        "token_type": token_pair.token_type,
        "expires_in": token_pair.expires_in,
        "user": {
            "id": user_id,
            "email": email,
            "roles": roles,
            "provider": oauth2_provider.value,
        },
    }

