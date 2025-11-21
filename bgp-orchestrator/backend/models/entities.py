"""
SQLAlchemy ORM models for BGP-related entities.
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
    Table,
    func,
)
from sqlalchemy.orm import relationship

from models.peering import Base


# Association table for many-to-many relationship between peerings and tags
peering_tags = Table(
    "peering_tags",
    Base.metadata,
    Column("peering_id", Integer, ForeignKey("bgp_peerings.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    """Tag model for flexible categorization."""

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    color = Column(String(7), nullable=False, default="#3B82F6")  # Hex color
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    # Relationships
    peerings = relationship("BGPPeering", secondary=peering_tags, back_populates="tags")

    __table_args__ = (
        Index("idx_tag_slug", "slug"),
    )

    def __repr__(self) -> str:
        return f"<Tag(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class AutonomousSystem(Base):
    """Autonomous System model."""

    __tablename__ = "autonomous_systems"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    asn = Column(BigInteger, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="active", index=True)
    rir = Column(String(10), nullable=True, comment="Regional Internet Registry (ARIN, RIPE, etc.)")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    # Relationships
    peer_groups = relationship("PeerGroup", back_populates="autonomous_system")
    peer_endpoints = relationship("PeerEndpoint", back_populates="autonomous_system")
    tags = relationship("Tag", secondary="as_tags", back_populates="autonomous_systems")

    __table_args__ = (
        Index("idx_as_asn", "asn"),
        Index("idx_as_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<AutonomousSystem(id={self.id}, asn={self.asn})>"


# Association table for AS tags
as_tags = Table(
    "as_tags",
    Base.metadata,
    Column("as_id", Integer, ForeignKey("autonomous_systems.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class PeerGroup(Base):
    """Peer Group model for template-based BGP configuration."""

    __tablename__ = "peer_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    device_id = Column(Integer, ForeignKey("autonomous_systems.id"), nullable=True)  # Reference to device/AS
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    autonomous_system_id = Column(Integer, ForeignKey("autonomous_systems.id"), nullable=True)
    import_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    export_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    source_ip_address = Column(String(45), nullable=True)
    source_interface = Column(String(255), nullable=True)
    template_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    # Relationships
    autonomous_system = relationship("AutonomousSystem", foreign_keys=[autonomous_system_id], back_populates="peer_groups")
    tags = relationship("Tag", secondary="peer_group_tags", back_populates="peer_groups")
    import_policy = relationship("RoutingPolicy", foreign_keys=[import_policy_id])
    export_policy = relationship("RoutingPolicy", foreign_keys=[export_policy_id])

    __table_args__ = (
        Index("idx_peer_group_name", "name"),
        Index("idx_peer_group_device", "device_id"),
    )

    def __repr__(self) -> str:
        return f"<PeerGroup(id={self.id}, name='{self.name}')>"


# Association table for peer group tags
peer_group_tags = Table(
    "peer_group_tags",
    Base.metadata,
    Column("peer_group_id", Integer, ForeignKey("peer_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class PeerEndpoint(Base):
    """Peer Endpoint model for individual BGP peer endpoints."""

    __tablename__ = "peer_endpoints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    device_id = Column(Integer, nullable=True)  # Reference to device
    routing_instance_id = Column(Integer, nullable=True)
    peer_group_id = Column(Integer, ForeignKey("peer_groups.id"), nullable=True)
    source_ip_address = Column(String(45), nullable=False)
    source_interface = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    autonomous_system_id = Column(Integer, ForeignKey("autonomous_systems.id"), nullable=False)
    import_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    export_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    hold_time = Column(Integer, nullable=True)
    keepalive = Column(Integer, nullable=True)
    remote_endpoint_id = Column(Integer, ForeignKey("peer_endpoints.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    # Relationships
    autonomous_system = relationship("AutonomousSystem", back_populates="peer_endpoints")
    peer_group = relationship("PeerGroup", back_populates=None)
    import_policy = relationship("RoutingPolicy", foreign_keys=[import_policy_id])
    export_policy = relationship("RoutingPolicy", foreign_keys=[export_policy_id])
    tags = relationship("Tag", secondary="peer_endpoint_tags", back_populates="peer_endpoints")

    __table_args__ = (
        Index("idx_peer_endpoint_name", "name"),
        Index("idx_peer_endpoint_device", "device_id"),
        Index("idx_peer_endpoint_source_ip", "source_ip_address"),
    )

    def __repr__(self) -> str:
        return f"<PeerEndpoint(id={self.id}, name='{self.name}', source_ip='{self.source_ip_address}')>"


# Association table for peer endpoint tags
peer_endpoint_tags = Table(
    "peer_endpoint_tags",
    Base.metadata,
    Column("peer_endpoint_id", Integer, ForeignKey("peer_endpoints.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class RoutingPolicy(Base):
    """Routing Policy model for BGP policy configuration."""

    __tablename__ = "routing_policies"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False, default="standard")  # standard, community, as-path, etc.
    rules = Column(JSON, nullable=False, default=dict)
    priority = Column(Integer, default=100, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    __table_args__ = (
        Index("idx_routing_policy_name", "name"),
        Index("idx_routing_policy_type", "type"),
    )

    def __repr__(self) -> str:
        return f"<RoutingPolicy(id={self.id}, name='{self.name}', type='{self.type}')>"


class AddressFamily(Base):
    """Address Family (AFI-SAFI) model."""

    __tablename__ = "address_families"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    routing_instance_id = Column(Integer, nullable=False, index=True)
    afi = Column(String(10), nullable=False)  # ipv4, ipv6, etc.
    safi = Column(String(20), nullable=False)  # unicast, multicast, vpnv4, l2vpn-evpn, etc.
    enabled = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    __table_args__ = (
        Index("idx_address_family_instance", "routing_instance_id"),
        Index("idx_address_family_afi_safi", "afi", "safi"),
    )

    def __repr__(self) -> str:
        return f"<AddressFamily(id={self.id}, afi='{self.afi}', safi='{self.safi}')>"


# Update Tag relationships (using string references to avoid circular imports)
Tag.peer_groups = relationship("PeerGroup", secondary="peer_group_tags", back_populates="tags")
Tag.peer_endpoints = relationship("PeerEndpoint", secondary="peer_endpoint_tags", back_populates="tags")
Tag.autonomous_systems = relationship("AutonomousSystem", secondary="as_tags", back_populates="tags")
Tag.peerings = relationship("BGPPeering", secondary="peering_tags", back_populates="tags")

# Update PeerGroup relationships
PeerGroup.peer_endpoints = relationship("PeerEndpoint", back_populates="peer_group", foreign_keys="[PeerEndpoint.peer_group_id]")

