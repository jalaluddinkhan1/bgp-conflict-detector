"""
SQLAlchemy ORM models for BGP peering management.
"""
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class PeeringStatus(str, Enum):
    """BGP peering status values."""

    ACTIVE = "active"
    PENDING = "pending"
    DISABLED = "disabled"


class BGPPeering(Base):
    """SQLAlchemy model for BGP peering sessions."""

    __tablename__ = "bgp_peerings"

    # Primary key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # Basic peering information
    name = Column(String(255), nullable=False, index=True, comment="Peering session name")
    local_asn = Column(BigInteger, nullable=False, index=True, comment="Local ASN")
    peer_asn = Column(BigInteger, nullable=False, index=True, comment="Peer ASN")
    peer_ip = Column(String(45), nullable=False, comment="Peer IP address (IPv4 or IPv6)")
    hold_time = Column(Integer, nullable=False, comment="BGP hold time in seconds")
    keepalive = Column(Integer, nullable=False, comment="BGP keepalive interval in seconds")

    # Device and interface
    device = Column(String(255), nullable=False, index=True, comment="Device/router name")
    interface = Column(String(255), nullable=True, comment="Interface name")

    # Status
    status = Column(
        SQLEnum(PeeringStatus, name="peering_status"),
        nullable=False,
        default=PeeringStatus.PENDING,
        index=True,
        comment="Peering status",
    )

    # Address families (stored as JSON array)
    address_families = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of supported address families",
    )

    # Routing policy (stored as JSON)
    routing_policy = Column(
        JSON,
        nullable=False,
        default=dict,
        comment="Routing policy configuration",
    )

    # Soft delete fields
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Soft delete flag - marks record as deleted without removing it",
    )
    deleted_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp when record was soft deleted",
    )
    deleted_by = Column(
        String(255),
        nullable=True,
        comment="User who soft deleted the peering",
    )

    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())
    created_by = Column(String(255), nullable=True, comment="User who created the peering")
    updated_by = Column(String(255), nullable=True, comment="User who last updated the peering")

    # Relationships
    # audit_logs = relationship("AuditLog", back_populates="peering", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="peering_tags", back_populates="peerings", lazy="selectin")

    # Indexes for common queries
    __table_args__ = (
        Index("idx_peering_device_peer_ip", "device", "peer_ip"),
        Index("idx_peering_status", "status"),
        Index("idx_peering_peer_asn", "peer_asn"),
        Index("idx_peering_local_asn", "local_asn"),
    )

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<BGPPeering(id={self.id}, name='{self.name}', peer_ip='{self.peer_ip}', status='{self.status}')>"

