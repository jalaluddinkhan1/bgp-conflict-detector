"""
SQLAlchemy ORM model for storing detected anomalies.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, Index, Integer, JSON, String, Text, func

from models.peering import Base


class AnomalyType(str, Enum):
    """Types of anomalies that can be detected."""
    
    BGP_FLAP = "bgp_flap"
    CPU_TEMPERATURE = "cpu_temperature"
    INTERFACE_ERROR = "interface_error"
    OTHER = "other"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""
    
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Anomaly(Base):
    """SQLAlchemy model for storing detected anomalies."""
    
    __tablename__ = "anomalies"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    
    # Anomaly information
    metric_name = Column(String(255), nullable=False, index=True, comment="Name of the metric")
    anomaly_type = Column(
        SQLEnum(AnomalyType, name="anomaly_type"),
        nullable=False,
        index=True,
        comment="Type of anomaly",
    )
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True, comment="When the anomaly occurred")
    
    # Metric values
    value = Column(Float, nullable=False, comment="Actual metric value")
    expected_value = Column(Float, nullable=False, comment="Expected metric value from Prophet")
    deviation = Column(Float, nullable=False, comment="Deviation from expected value")
    
    # Severity and context
    severity = Column(
        SQLEnum(AnomalySeverity, name="anomaly_severity"),
        nullable=False,
        index=True,
        comment="Severity level",
    )
    device = Column(String(255), nullable=True, index=True, comment="Device/router name (if applicable)")
    
    # Additional metadata (stored as JSON)
    metadata = Column(
        JSON,
        nullable=True,
        comment="Additional metadata about the anomaly (sigma, bounds, etc.)",
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="When anomaly was detected")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_anomaly_metric_timestamp", "metric_name", "timestamp"),
        Index("idx_anomaly_device_timestamp", "device", "timestamp"),
        Index("idx_anomaly_severity_timestamp", "severity", "timestamp"),
    )
    
    def __repr__(self) -> str:
        """String representation of the model."""
        return (
            f"<Anomaly(id={self.id}, metric='{self.metric_name}', "
            f"type='{self.anomaly_type}', severity='{self.severity}', "
            f"timestamp='{self.timestamp}')>"
        )

