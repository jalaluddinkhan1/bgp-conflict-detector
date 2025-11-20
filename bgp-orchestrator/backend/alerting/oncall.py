"""
Grafana OnCall Integration for Incident Management

Provides integration with Grafana OnCall (formerly Grafana Incident) for:
- On-call rotations and escalations
- Alert routing and acknowledgment
- Auto-remediation with auto-acknowledge
- Slack notifications
"""
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

import httpx
from app.config import settings
from app.middleware.logging import logger


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, Enum):
    """Alert status."""
    
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SILENCED = "silenced"


class GrafanaOnCallClient:
    """
    Client for Grafana OnCall API.
    
    Handles incident creation, escalation, and management.
    """
    
    def __init__(
        self,
        base_url: str,
        api_token: str,
        timeout: float = 30.0,
    ):
        """
        Initialize Grafana OnCall client.
        
        Args:
            base_url: Grafana OnCall base URL (e.g., http://oncall:8080)
            api_token: API token for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            },
        )
    
    async def create_incident(
        self,
        title: str,
        description: str,
        severity: AlertSeverity,
        source: str = "bgp-orchestrator",
        labels: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict]:
        """
        Create a new incident in Grafana OnCall.
        
        Args:
            title: Incident title
            description: Incident description
            severity: Alert severity
            source: Source system
            labels: Optional labels for routing
            
        Returns:
            Incident data dictionary or None on error
        """
        try:
            payload = {
                "title": title,
                "description": description,
                "severity": severity.value,
                "source": source,
                "labels": labels or {},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/incidents",
                json=payload,
            )
            response.raise_for_status()
            
            incident = response.json()
            logger.info(
                f"Incident created in Grafana OnCall",
                incident_id=incident.get("id"),
                title=title,
                severity=severity.value,
            )
            
            return incident
            
        except Exception as e:
            logger.error(f"Failed to create incident in Grafana OnCall: {e}", exc_info=True)
            return None
    
    async def acknowledge_incident(self, incident_id: str, reason: Optional[str] = None) -> bool:
        """
        Acknowledge an incident.
        
        Args:
            incident_id: Incident ID
            reason: Optional acknowledgment reason
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "status": AlertStatus.ACKNOWLEDGED.value,
                "acknowledged_at": datetime.now(timezone.utc).isoformat(),
            }
            if reason:
                payload["acknowledgment_reason"] = reason
            
            response = await self.client.patch(
                f"{self.base_url}/api/v1/incidents/{incident_id}",
                json=payload,
            )
            response.raise_for_status()
            
            logger.info(f"Incident acknowledged", incident_id=incident_id, reason=reason)
            return True
            
        except Exception as e:
            logger.error(f"Failed to acknowledge incident: {e}", exc_info=True)
            return False
    
    async def resolve_incident(self, incident_id: str, resolution: Optional[str] = None) -> bool:
        """
        Resolve an incident.
        
        Args:
            incident_id: Incident ID
            resolution: Optional resolution notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "status": AlertStatus.RESOLVED.value,
                "resolved_at": datetime.now(timezone.utc).isoformat(),
            }
            if resolution:
                payload["resolution"] = resolution
            
            response = await self.client.patch(
                f"{self.base_url}/api/v1/incidents/{incident_id}",
                json=payload,
            )
            response.raise_for_status()
            
            logger.info(f"Incident resolved", incident_id=incident_id, resolution=resolution)
            return True
            
        except Exception as e:
            logger.error(f"Failed to resolve incident: {e}", exc_info=True)
            return False
    
    async def get_oncall_user(self, schedule_name: str) -> Optional[Dict]:
        """
        Get current on-call user for a schedule.
        
        Args:
            schedule_name: Schedule name
            
        Returns:
            On-call user data or None
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v1/schedules/{schedule_name}/oncall",
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get on-call user: {e}", exc_info=True)
            return None
    
    async def escalate_incident(self, incident_id: str, escalation_policy: str) -> bool:
        """
        Escalate an incident using an escalation policy.
        
        Args:
            incident_id: Incident ID
            escalation_policy: Escalation policy name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            payload = {
                "escalation_policy": escalation_policy,
                "escalated_at": datetime.now(timezone.utc).isoformat(),
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/v1/incidents/{incident_id}/escalate",
                json=payload,
            )
            response.raise_for_status()
            
            logger.info(
                f"Incident escalated",
                incident_id=incident_id,
                escalation_policy=escalation_policy,
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to escalate incident: {e}", exc_info=True)
            return False
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class SlackNotifier:
    """Slack integration for sending alerts to #noc-alerts channel."""
    
    def __init__(self, webhook_url: str):
        """
        Initialize Slack notifier.
        
        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url
        self.client = httpx.AsyncClient()
    
    async def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        incident_id: Optional[str] = None,
    ) -> bool:
        """
        Send alert to Slack #noc-alerts channel.
        
        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            incident_id: Optional incident ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Color mapping for severity
            color_map = {
                AlertSeverity.CRITICAL: "#FF0000",  # Red
                AlertSeverity.HIGH: "#FF8C00",      # Orange
                AlertSeverity.MEDIUM: "#FFD700",    # Gold
                AlertSeverity.LOW: "#87CEEB",       # Sky Blue
                AlertSeverity.INFO: "#808080",      # Gray
            }
            
            payload = {
                "channel": "#noc-alerts",
                "username": "BGP Orchestrator",
                "icon_emoji": ":rotating_light:",
                "attachments": [
                    {
                        "color": color_map.get(severity, "#808080"),
                        "title": title,
                        "text": message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": severity.value.upper(),
                                "short": True,
                            },
                            {
                                "title": "Time",
                                "value": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "short": True,
                            },
                        ],
                        "footer": "BGP Orchestrator",
                        "ts": int(datetime.now(timezone.utc).timestamp()),
                    }
                ],
            }
            
            if incident_id:
                payload["attachments"][0]["fields"].append({
                    "title": "Incident ID",
                    "value": incident_id,
                    "short": True,
                })
            
            response = await self.client.post(
                self.webhook_url,
                json=payload,
            )
            response.raise_for_status()
            
            logger.info(f"Alert sent to Slack", title=title, severity=severity.value)
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}", exc_info=True)
            return False
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()


class IncidentManager:
    """
    Incident manager for BGP Orchestrator.
    
    Handles incident creation, escalation, and auto-remediation.
    """
    
    def __init__(
        self,
        oncall_client: Optional[GrafanaOnCallClient] = None,
        slack_notifier: Optional[SlackNotifier] = None,
    ):
        """
        Initialize incident manager.
        
        Args:
            oncall_client: Grafana OnCall client (optional)
            slack_notifier: Slack notifier (optional)
        """
        self.oncall_client = oncall_client
        self.slack_notifier = slack_notifier
        self.auto_remediation_enabled = True
    
    async def handle_bgp_hijack(
        self,
        hijack_details: Dict,
        auto_remediate: bool = False,
    ) -> Optional[str]:
        """
        Handle BGP hijack incident.
        
        Args:
            hijack_details: Hijack details dictionary
            auto_remediate: Whether to attempt auto-remediation
            
        Returns:
            Incident ID if created, None otherwise
        """
        title = f"BGP Hijack Detected: {hijack_details.get('prefix', 'Unknown')}"
        description = f"""
BGP Hijack Detected

Prefix: {hijack_details.get('prefix')}
Origin ASN: {hijack_details.get('origin_asn')}
Hijacker ASN: {hijack_details.get('hijacker_asn')}
Detected At: {hijack_details.get('detected_at')}
Severity: CRITICAL

Details:
{hijack_details.get('details', 'No additional details')}
        """.strip()
        
        # Create incident
        incident = None
        if self.oncall_client:
            incident = await self.oncall_client.create_incident(
                title=title,
                description=description,
                severity=AlertSeverity.CRITICAL,
                source="bgp-orchestrator",
                labels={
                    "type": "bgp_hijack",
                    "prefix": hijack_details.get("prefix", ""),
                    "severity": "critical",
                },
            )
        
        # Send Slack notification
        if self.slack_notifier:
            await self.slack_notifier.send_alert(
                title=title,
                message=description,
                severity=AlertSeverity.CRITICAL,
                incident_id=incident.get("id") if incident else None,
            )
        
        # Auto-remediation
        if auto_remediate and self.auto_remediation_enabled:
            remediation_success = await self._auto_remediate_hijack(hijack_details)
            
            if remediation_success and incident:
                # Auto-acknowledge if remediated
                await self.oncall_client.acknowledge_incident(
                    incident.get("id"),
                    reason="Auto-remediated successfully",
                )
                logger.info("BGP hijack auto-remediated and acknowledged")
        
        return incident.get("id") if incident else None
    
    async def _auto_remediate_hijack(self, hijack_details: Dict) -> bool:
        """
        Attempt to auto-remediate BGP hijack.
        
        Args:
            hijack_details: Hijack details
            
        Returns:
            True if remediation successful, False otherwise
        """
        logger.info("Auto-remediation attempted", hijack_details=hijack_details)
        return False  # Placeholder
    
    async def handle_service_down(
        self,
        service_name: str,
        error_message: str,
    ) -> Optional[str]:
        """
        Handle service down incident.
        
        Args:
            service_name: Name of the service
            error_message: Error message
            
        Returns:
            Incident ID if created, None otherwise
        """
        title = f"Service Down: {service_name}"
        description = f"""
Service {service_name} is down or unreachable.

Error: {error_message}
Time: {datetime.now(timezone.utc).isoformat()}
        """.strip()
        
        incident = None
        if self.oncall_client:
            incident = await self.oncall_client.create_incident(
                title=title,
                description=description,
                severity=AlertSeverity.HIGH,
                source="bgp-orchestrator",
                labels={
                    "type": "service_down",
                    "service": service_name,
                },
            )
        
        if self.slack_notifier:
            await self.slack_notifier.send_alert(
                title=title,
                message=description,
                severity=AlertSeverity.HIGH,
                incident_id=incident.get("id") if incident else None,
            )
        
        return incident.get("id") if incident else None


# Global incident manager instance
_incident_manager: Optional[IncidentManager] = None


def get_incident_manager() -> Optional[IncidentManager]:
    """Get or create incident manager instance."""
    global _incident_manager
    
    oncall_enabled = getattr(settings, "ONCALL_ENABLED", False)
    if not oncall_enabled:
        return None
    
    if _incident_manager is None:
        oncall_client = None
        slack_notifier = None
        
        # Initialize Grafana OnCall client
        oncall_url = getattr(settings, "ONCALL_URL", None)
        oncall_token = getattr(settings, "ONCALL_API_TOKEN", None)
        if oncall_url and oncall_token:
            oncall_client = GrafanaOnCallClient(
                base_url=oncall_url,
                api_token=oncall_token,
            )
        
        # Initialize Slack notifier
        slack_webhook = getattr(settings, "SLACK_WEBHOOK_URL", None)
        if slack_webhook:
            slack_notifier = SlackNotifier(webhook_url=slack_webhook)
        
        _incident_manager = IncidentManager(
            oncall_client=oncall_client,
            slack_notifier=slack_notifier,
        )
    
    return _incident_manager

