"""
Alert message templates.
"""
from typing import Any, Optional


class AlertTemplate:
    """Alert message template."""

    @staticmethod
    def conflict_alert(conflict_type: str, severity: str, description: str, **kwargs) -> str:
        """
        Generate conflict alert message.
        
        Args:
            conflict_type: Type of conflict
            severity: Conflict severity
            description: Conflict description
            **kwargs: Additional context
            
        Returns:
            Formatted alert message
        """
        message = f"🚨 BGP Conflict Detected\n\n"
        message += f"Type: {conflict_type}\n"
        message += f"Severity: {severity.upper()}\n"
        message += f"Description: {description}\n"
        
        if "affected_peers" in kwargs:
            message += f"Affected Peers: {kwargs['affected_peers']}\n"
        
        if "recommended_action" in kwargs:
            message += f"\nRecommended Action: {kwargs['recommended_action']}\n"
        
        return message

    @staticmethod
    def anomaly_alert(metric: str, value: float, threshold: float, **kwargs) -> str:
        """
        Generate anomaly alert message.
        
        Args:
            metric: Metric name
            value: Current value
            threshold: Threshold value
            **kwargs: Additional context
            
        Returns:
            Formatted alert message
        """
        message = f"⚠️ Anomaly Detected\n\n"
        message += f"Metric: {metric}\n"
        message += f"Value: {value}\n"
        message += f"Threshold: {threshold}\n"
        
        if "device" in kwargs:
            message += f"Device: {kwargs['device']}\n"
        
        if "timestamp" in kwargs:
            message += f"Timestamp: {kwargs['timestamp']}\n"
        
        return message

    @staticmethod
    def ml_prediction_alert(flap_probability: float, confidence: float, **kwargs) -> str:
        """
        Generate ML prediction alert message.
        
        Args:
            flap_probability: Predicted flap probability
            confidence: Model confidence
            **kwargs: Additional context
            
        Returns:
            Formatted alert message
        """
        message = f"🤖 High BGP Flap Probability Predicted\n\n"
        message += f"Flap Probability: {flap_probability:.2%}\n"
        message += f"Confidence: {confidence:.2%}\n"
        
        if "peer_ip" in kwargs:
            message += f"Peer: {kwargs['peer_ip']}\n"
        
        return message


def render_alert(template_type: str, **kwargs) -> str:
    """
    Render alert message from template.
    
    Args:
        template_type: Template type (conflict, anomaly, ml_prediction)
        **kwargs: Template parameters
        
    Returns:
        Rendered alert message
    """
    template = AlertTemplate()
    
    if template_type == "conflict":
        return template.conflict_alert(**kwargs)
    elif template_type == "anomaly":
        return template.anomaly_alert(**kwargs)
    elif template_type == "ml_prediction":
        return template.ml_prediction_alert(**kwargs)
    else:
        return str(kwargs)

