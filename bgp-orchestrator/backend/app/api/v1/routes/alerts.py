"""
Alerting API endpoints for sending and managing alerts.
"""
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession, require_role
from app.middleware.logging import logger
from app.config import settings
from alerting.notifiers import AlertNotifier, OnCallNotifier, SlackNotifier
from alerting.oncall import (
    AlertSeverity,
    AlertStatus,
    GrafanaOnCallClient,
    get_incident_manager,
)
from security.auth import UserRole

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertCreate(BaseModel):
    """Request model for creating an alert."""

    title: str = Field(..., description="Alert title", min_length=1, max_length=200)
    message: str = Field(..., description="Alert message", min_length=1)
    severity: AlertSeverity = Field(
        default=AlertSeverity.MEDIUM,
        description="Alert severity level",
    )
    source: str = Field(
        default="api",
        description="Source of the alert",
        max_length=100,
    )
    labels: Optional[dict[str, str]] = Field(
        default=None,
        description="Optional labels for routing and filtering",
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional metadata",
    )


class AlertResponse(BaseModel):
    """Response model for alert."""

    id: Optional[str] = Field(None, description="Alert/incident ID")
    title: str
    message: str
    severity: str
    status: str
    source: str
    created_at: datetime
    labels: Optional[dict[str, str]] = None
    metadata: Optional[dict] = None


class AlertAcknowledge(BaseModel):
    """Request model for acknowledging an alert."""

    reason: Optional[str] = Field(None, description="Acknowledgment reason", max_length=500)


class AlertResolve(BaseModel):
    """Request model for resolving an alert."""

    resolution: Optional[str] = Field(None, description="Resolution notes", max_length=1000)


# Global notifiers
_slack_notifier: Optional[SlackNotifier] = None
_oncall_client: Optional[GrafanaOnCallClient] = None


def get_slack_notifier() -> Optional[SlackNotifier]:
    """Get or create Slack notifier instance."""
    global _slack_notifier
    if _slack_notifier is None and settings.SLACK_WEBHOOK_URL:
        _slack_notifier = SlackNotifier(webhook_url=settings.SLACK_WEBHOOK_URL)
    return _slack_notifier


def get_oncall_client() -> Optional[GrafanaOnCallClient]:
    """Get or create Grafana OnCall client instance."""
    global _oncall_client
    if _oncall_client is None and settings.ONCALL_ENABLED and settings.ONCALL_URL and settings.ONCALL_API_TOKEN:
        _oncall_client = GrafanaOnCallClient(
            base_url=settings.ONCALL_URL,
            api_token=settings.ONCALL_API_TOKEN,
        )
    return _oncall_client


@router.post(
    "/",
    response_model=AlertResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send alert",
    description="Send an alert to configured notification channels (Slack, Grafana OnCall, etc.)",
)
@limiter.limit("10/minute")
async def send_alert(
    request: Request,
    alert_data: AlertCreate,
    user: CurrentUser,
) -> AlertResponse:
    """
    Send an alert to configured notification channels.
    
    - Sends to Slack if webhook is configured
    - Creates incident in Grafana OnCall if enabled
    - Returns alert details with incident ID if created
    """
    created_at = datetime.now(timezone.utc)
    incident_id = None
    
    # Send to Grafana OnCall if enabled
    oncall_client = get_oncall_client()
    if oncall_client:
        try:
            incident = await oncall_client.create_incident(
                title=alert_data.title,
                description=alert_data.message,
                severity=alert_data.severity,
                source=alert_data.source,
                labels=alert_data.labels or {},
            )
            if incident:
                incident_id = incident.get("id")
                logger.info(
                    "Alert sent to Grafana OnCall",
                    incident_id=incident_id,
                    title=alert_data.title,
                    severity=alert_data.severity.value,
                    user=user.email,
                )
        except Exception as e:
            logger.error(f"Failed to send alert to Grafana OnCall: {e}", exc_info=True)
    
    # Send to Slack if configured
    slack_notifier = get_slack_notifier()
    if slack_notifier:
        try:
            await slack_notifier.send(
                message=f"{alert_data.title}\n\n{alert_data.message}",
                severity=alert_data.severity.value,
                metadata=alert_data.metadata or {},
            )
            logger.info(
                "Alert sent to Slack",
                title=alert_data.title,
                severity=alert_data.severity.value,
                user=user.email,
            )
        except Exception as e:
            logger.error(f"Failed to send alert to Slack: {e}", exc_info=True)
    
    # If no notifiers are configured, log warning
    if not oncall_client and not slack_notifier:
        logger.warning(
            "No alerting channels configured",
            title=alert_data.title,
            user=user.email,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No alerting channels configured. Please configure Slack webhook or Grafana OnCall.",
        )
    
    return AlertResponse(
        id=incident_id,
        title=alert_data.title,
        message=alert_data.message,
        severity=alert_data.severity.value,
        status=AlertStatus.FIRING.value,
        source=alert_data.source,
        created_at=created_at,
        labels=alert_data.labels,
        metadata=alert_data.metadata,
    )


@router.post(
    "/{alert_id}/acknowledge",
    response_model=dict,
    summary="Acknowledge alert",
    description="Acknowledge an alert/incident in Grafana OnCall",
)
@limiter.limit("10/minute")
async def acknowledge_alert(
    request: Request,
    alert_id: str,
    ack_data: AlertAcknowledge,
    user: CurrentUser,
) -> dict:
    """
    Acknowledge an alert/incident.
    
    Requires OPERATOR or ADMIN role.
    """
    oncall_client = get_oncall_client()
    if not oncall_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grafana OnCall is not configured",
        )
    
    try:
        success = await oncall_client.acknowledge_incident(
            incident_id=alert_id,
            reason=ack_data.reason,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to acknowledge incident",
            )
        
        logger.info(
            "Alert acknowledged",
            alert_id=alert_id,
            reason=ack_data.reason,
            user=user.email,
        )
        
        return {
            "status": "acknowledged",
            "alert_id": alert_id,
            "acknowledged_by": user.email,
            "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to acknowledge alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to acknowledge alert: {str(e)}",
        )


@router.post(
    "/{alert_id}/resolve",
    response_model=dict,
    summary="Resolve alert",
    description="Resolve an alert/incident in Grafana OnCall",
)
@limiter.limit("10/minute")
async def resolve_alert(
    request: Request,
    alert_id: str,
    resolve_data: AlertResolve,
    user: CurrentUser,
) -> dict:
    """
    Resolve an alert/incident.
    
    Requires OPERATOR or ADMIN role.
    """
    oncall_client = get_oncall_client()
    if not oncall_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grafana OnCall is not configured",
        )
    
    try:
        success = await oncall_client.resolve_incident(
            incident_id=alert_id,
            resolution=resolve_data.resolution,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to resolve incident",
            )
        
        logger.info(
            "Alert resolved",
            alert_id=alert_id,
            resolution=resolve_data.resolution,
            user=user.email,
        )
        
        return {
            "status": "resolved",
            "alert_id": alert_id,
            "resolved_by": user.email,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to resolve alert: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve alert: {str(e)}",
        )


@router.get(
    "/channels",
    response_model=dict,
    summary="List alert channels",
    description="Get list of configured alerting channels",
)
async def list_alert_channels(
    user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
) -> dict:
    """
    List configured alerting channels.
    
    Requires OPERATOR or ADMIN role.
    """
    channels = {
        "slack": {
            "enabled": settings.SLACK_WEBHOOK_URL is not None,
            "configured": bool(settings.SLACK_WEBHOOK_URL),
        },
        "grafana_oncall": {
            "enabled": settings.ONCALL_ENABLED,
            "configured": bool(settings.ONCALL_URL and settings.ONCALL_API_TOKEN),
            "url": settings.ONCALL_URL if settings.ONCALL_ENABLED else None,
            "schedule": settings.ONCALL_SCHEDULE_NAME if settings.ONCALL_ENABLED else None,
        },
    }
    
    return {
        "channels": channels,
        "any_configured": bool(settings.SLACK_WEBHOOK_URL or (settings.ONCALL_ENABLED and settings.ONCALL_URL)),
    }


@router.get(
    "/oncall/current",
    response_model=dict,
    summary="Get current on-call",
    description="Get current on-call user for the configured schedule",
)
async def get_current_oncall(
    user: Annotated[CurrentUser, Depends(require_role(UserRole.ADMIN, UserRole.OPERATOR))],
) -> dict:
    """
    Get current on-call user.
    
    Requires OPERATOR or ADMIN role.
    """
    oncall_client = get_oncall_client()
    if not oncall_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Grafana OnCall is not configured",
        )
    
    try:
        oncall_user = await oncall_client.get_oncall_user(settings.ONCALL_SCHEDULE_NAME)
        if not oncall_user:
            return {
                "schedule": settings.ONCALL_SCHEDULE_NAME,
                "oncall_user": None,
                "message": "No on-call user found for this schedule",
            }
        
        return {
            "schedule": settings.ONCALL_SCHEDULE_NAME,
            "oncall_user": oncall_user,
        }
    except Exception as e:
        logger.error(f"Failed to get on-call user: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get on-call user: {str(e)}",
        )

