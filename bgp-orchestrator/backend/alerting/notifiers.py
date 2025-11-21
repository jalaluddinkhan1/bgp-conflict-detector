"""
Alert notification channels.
"""
from abc import ABC, abstractmethod
from typing import Any, Optional

import httpx


class AlertNotifier(ABC):
    """Abstract base class for alert notifiers."""

    @abstractmethod
    async def send(self, message: str, severity: str, metadata: Optional[dict[str, Any]] = None) -> bool:
        """
        Send alert notification.
        
        Args:
            message: Alert message
            severity: Alert severity (critical, high, medium, low)
            metadata: Additional metadata
            
        Returns:
            True if sent successfully
        """


class SlackNotifier(AlertNotifier):
    """Slack webhook notifier."""

    def __init__(self, webhook_url: str):
        """
        Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url

    async def send(
        self, message: str, severity: str, metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """Send alert to Slack."""
        color_map = {
            "critical": "#ff0000",
            "high": "#ff8800",
            "medium": "#ffaa00",
            "low": "#00aa00",
        }

        payload = {
            "text": f"BGP Alert: {severity.upper()}",
            "attachments": [
                {
                    "color": color_map.get(severity.lower(), "#888888"),
                    "text": message,
                    "fields": [
                        {"title": "Severity", "value": severity, "short": True}
                    ],
                }
            ],
        }

        if metadata:
            for key, value in metadata.items():
                payload["attachments"][0]["fields"].append(
                    {"title": key, "value": str(value), "short": True}
                )

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.webhook_url, json=payload)
                return response.status_code == 200
        except Exception:
            return False


class EmailNotifier(AlertNotifier):
    """Email notifier (placeholder - requires SMTP configuration)."""

    def __init__(self, smtp_host: str, smtp_port: int, from_email: str, to_emails: list[str]):
        """
        Initialize email notifier.
        
        Args:
            smtp_host: SMTP server host
            smtp_port: SMTP server port
            from_email: From email address
            to_emails: List of recipient email addresses
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.to_emails = to_emails

    async def send(
        self, message: str, severity: str, metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """Send alert via email."""
        # Placeholder - implement SMTP sending
        return False


class OnCallNotifier(AlertNotifier):
    """Grafana OnCall notifier."""

    def __init__(self, api_url: str, api_token: str, schedule_name: str):
        """
        Initialize OnCall notifier.
        
        Args:
            api_url: Grafana OnCall API URL
            api_token: API token
            schedule_name: OnCall schedule name
        """
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.schedule_name = schedule_name
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }

    async def send(
        self, message: str, severity: str, metadata: Optional[dict[str, Any]] = None
    ) -> bool:
        """Send alert to Grafana OnCall."""
        payload = {
            "title": f"BGP Alert: {severity.upper()}",
            "message": message,
            "severity": severity.upper(),
            "source": "bgp-detector",
        }

        if metadata:
            payload["details"] = metadata

        try:
            async with httpx.AsyncClient() as client:
                # Create alert group
                response = await client.post(
                    f"{self.api_url}/api/v1/alert_groups/",
                    json=payload,
                    headers=self.headers,
                )
                return response.status_code in (200, 201)
        except Exception:
            return False

