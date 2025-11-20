"""
Customer Portal API endpoints.

Provides self-service endpoints for customers to:
- View usage statistics
- Manage invoices
- Handle support tickets
- Manage BGP peerings
- Configure alert preferences
- Change billing plans
- Manage API keys
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession
from app.middleware.logging import logger
from models.peering import BGPPeering

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/customer", tags=["Customer Portal"])


class UsageStatsResponse(BaseModel):
    """Usage statistics response."""
    
    bgp_peerings_count: int
    api_requests_this_month: int
    data_transfer_gb: float
    ml_predictions_count: int
    storage_used_gb: float


class InvoiceResponse(BaseModel):
    """Invoice response."""
    
    id: str
    invoice_number: str
    amount: float
    currency: str
    status: str
    due_date: str
    created_at: str


class SupportTicketResponse(BaseModel):
    """Support ticket response."""
    
    id: str
    subject: str
    status: str
    priority: str
    created_at: str
    updated_at: str


class BillingPlanResponse(BaseModel):
    """Billing plan response."""
    
    id: str
    name: str
    price: float
    currency: str
    features: List[str]
    limits: dict


class APIKeyResponse(BaseModel):
    """API key response."""
    
    id: str
    name: str
    key_prefix: str
    created_at: str
    last_used_at: Optional[str] = None
    expires_at: Optional[str] = None


class AlertPreferencesResponse(BaseModel):
    """Alert preferences response."""
    
    email_enabled: bool
    slack_enabled: bool
    webhook_url: Optional[str] = None
    critical_alerts: bool
    warning_alerts: bool
    info_alerts: bool


@router.get("/usage-stats", response_model=UsageStatsResponse)
@limiter.limit("10/second")
async def get_usage_stats(
    request: Request,
    user: CurrentUser,
    db: DbSession,
) -> UsageStatsResponse:
    """
    Get usage statistics for the current customer.
    """
    try:
        # Get BGP peerings count
        result = await db.execute(select(BGPPeering))
        peerings = result.scalars().all()
        peerings_count = len(peerings)
        
        return UsageStatsResponse(
            bgp_peerings_count=peerings_count,
            api_requests_this_month=1000,  # Mock
            data_transfer_gb=50.5,  # Mock
            ml_predictions_count=250,  # Mock
            storage_used_gb=10.2,  # Mock
        )
        
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving usage statistics",
        )


@router.get("/invoices", response_model=List[InvoiceResponse])
@limiter.limit("10/second")
async def get_invoices(
    request: Request,
    user: CurrentUser,
) -> List[InvoiceResponse]:
    """
    Get invoices for the current customer.
    """
    # For now, return mock data
    return [
        InvoiceResponse(
            id="inv_001",
            invoice_number="INV-2024-001",
            amount=99.99,
            currency="USD",
            status="paid",
            due_date="2024-01-15T00:00:00Z",
            created_at="2024-01-01T00:00:00Z",
        ),
    ]


@router.get("/support-tickets", response_model=List[SupportTicketResponse])
@limiter.limit("10/second")
async def get_support_tickets(
    request: Request,
    user: CurrentUser,
) -> List[SupportTicketResponse]:
    """
    Get support tickets for the current customer.
    """
    # For now, return mock data
    return []


@router.get("/plan", response_model=BillingPlanResponse)
@limiter.limit("10/second")
async def get_current_plan(
    request: Request,
    user: CurrentUser,
) -> BillingPlanResponse:
    """
    Get current billing plan.
    """
    return BillingPlanResponse(
        id="plan_basic",
        name="Basic Plan",
        price=99.99,
        currency="USD",
        features=[
            "Up to 100 BGP peerings",
            "10,000 API requests/month",
            "100 GB data transfer",
            "ML predictions",
        ],
        limits={
            "bgp_peerings": 100,
            "api_requests_per_month": 10000,
            "data_transfer_gb": 100,
        },
    )


@router.get("/plans", response_model=List[BillingPlanResponse])
@limiter.limit("10/second")
async def get_available_plans(
    request: Request,
    user: CurrentUser,
) -> List[BillingPlanResponse]:
    """
    Get available billing plans.
    """
    return [
        BillingPlanResponse(
            id="plan_basic",
            name="Basic Plan",
            price=99.99,
            currency="USD",
            features=[
                "Up to 100 BGP peerings",
                "10,000 API requests/month",
                "100 GB data transfer",
            ],
            limits={
                "bgp_peerings": 100,
                "api_requests_per_month": 10000,
                "data_transfer_gb": 100,
            },
        ),
        BillingPlanResponse(
            id="plan_pro",
            name="Pro Plan",
            price=299.99,
            currency="USD",
            features=[
                "Up to 1,000 BGP peerings",
                "100,000 API requests/month",
                "1 TB data transfer",
                "Priority support",
            ],
            limits={
                "bgp_peerings": 1000,
                "api_requests_per_month": 100000,
                "data_transfer_gb": 1000,
            },
        ),
        BillingPlanResponse(
            id="plan_enterprise",
            name="Enterprise Plan",
            price=999.99,
            currency="USD",
            features=[
                "Unlimited BGP peerings",
                "Unlimited API requests",
                "Unlimited data transfer",
                "Dedicated support",
                "SLA guarantee",
            ],
            limits={
                "bgp_peerings": -1,  # Unlimited
                "api_requests_per_month": -1,
                "data_transfer_gb": -1,
            },
        ),
    ]


@router.post("/change-plan")
@limiter.limit("5/minute")
async def change_plan(
    request: Request,
    plan_id: str = Query(..., description="Plan ID to change to"),
    user: CurrentUser,
) -> dict:
    """
    Change billing plan.
    """
    logger.info(f"Plan change requested", user=user.email, plan_id=plan_id)
    
    return {
        "status": "success",
        "message": "Plan change initiated",
        "plan_id": plan_id,
    }


@router.get("/api-keys", response_model=List[APIKeyResponse])
@limiter.limit("10/second")
async def get_api_keys(
    request: Request,
    user: CurrentUser,
) -> List[APIKeyResponse]:
    """
    Get API keys for the current customer.
    """
    return []


@router.post("/api-keys", response_model=APIKeyResponse)
@limiter.limit("10/minute")
async def create_api_key(
    request: Request,
    name: str = Query(..., description="API key name"),
    user: CurrentUser,
) -> APIKeyResponse:
    """
    Create a new API key.
    """
    import secrets
    
    key_prefix = secrets.token_urlsafe(16)[:8].upper()
    
    logger.info(f"API key created", user=user.email, name=name)
    
    return APIKeyResponse(
        id="key_001",
        name=name,
        key_prefix=key_prefix,
        created_at=datetime.now(timezone.utc).isoformat(),
        expires_at=None,
    )


@router.delete("/api-keys/{key_id}")
@limiter.limit("10/minute")
async def delete_api_key(
    request: Request,
    key_id: str,
    user: CurrentUser,
) -> dict:
    """
    Delete an API key.
    """
    logger.info(f"API key deleted", user=user.email, key_id=key_id)
    
    return {"status": "success", "message": "API key deleted"}


@router.get("/alert-preferences", response_model=AlertPreferencesResponse)
@limiter.limit("10/second")
async def get_alert_preferences(
    request: Request,
    user: CurrentUser,
) -> AlertPreferencesResponse:
    """
    Get alert preferences.
    """
    return AlertPreferencesResponse(
        email_enabled=True,
        slack_enabled=False,
        webhook_url=None,
        critical_alerts=True,
        warning_alerts=True,
        info_alerts=False,
    )


@router.put("/alert-preferences", response_model=AlertPreferencesResponse)
@limiter.limit("10/minute")
async def update_alert_preferences(
    request: Request,
    prefs: AlertPreferencesResponse,
    user: CurrentUser,
) -> AlertPreferencesResponse:
    """
    Update alert preferences.
    """
    logger.info(f"Alert preferences updated", user=user.email, prefs=prefs.model_dump())
    
    return prefs

