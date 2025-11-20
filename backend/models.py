from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, JSON, Float, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class AddressFamilyType(str, enum.Enum):
    IPV4_UNICAST = "ipv4_unicast"
    IPV6_UNICAST = "ipv6_unicast"
    VPNV4_UNICAST = "vpnv4_unicast"
    VPNV6_UNICAST = "vpnv6_unicast"
    L2VPN_EVPN = "l2vpn_evpn"


class BGPStateType(str, enum.Enum):
    IDLE = "idle"
    CONNECT = "connect"
    ACTIVE = "active"
    OPENSENT = "opensent"
    OPENCONFIRM = "openconfirm"
    ESTABLISHED = "established"


class AuthenticationType(str, enum.Enum):
    MD5 = "md5"
    TCP_AO = "tcp_ao"


class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="Active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AutonomousSystem(Base):
    __tablename__ = "autonomous_systems"
    
    id = Column(Integer, primary_key=True, index=True)
    asn = Column(Integer, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="Active")
    rir = Column(String, nullable=True)  # Regional Internet Registry
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tags = relationship("Tag", secondary="as_tags", back_populates="autonomous_systems")


class RoutingInstance(Base):
    __tablename__ = "routing_instances"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    autonomous_system_id = Column(Integer, ForeignKey("autonomous_systems.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    device = relationship("Device", backref="routing_instances")
    autonomous_system = relationship("AutonomousSystem", backref="routing_instances")


class PeerGroupTemplate(Base):
    __tablename__ = "peer_group_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PeerGroup(Base):
    __tablename__ = "peer_groups"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    routing_instance_id = Column(Integer, ForeignKey("routing_instances.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("peer_group_templates.id"), nullable=True)
    source_ip_address = Column(String, nullable=True)
    source_interface = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    autonomous_system_id = Column(Integer, ForeignKey("autonomous_systems.id"), nullable=True)
    import_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    export_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    device = relationship("Device", backref="peer_groups")
    routing_instance = relationship("RoutingInstance", backref="peer_groups")
    template = relationship("PeerGroupTemplate", backref="peer_groups")
    autonomous_system = relationship("AutonomousSystem", backref="peer_groups")
    import_policy = relationship("RoutingPolicy", foreign_keys=[import_policy_id], backref="peer_groups_import")
    export_policy = relationship("RoutingPolicy", foreign_keys=[export_policy_id], backref="peer_groups_export")
    tags = relationship("Tag", secondary="peer_group_tags", back_populates="peer_groups")


class PeerEndpoint(Base):
    __tablename__ = "peer_endpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    routing_instance_id = Column(Integer, ForeignKey("routing_instances.id"), nullable=False)
    peer_group_id = Column(Integer, ForeignKey("peer_groups.id"), nullable=True)
    source_ip_address = Column(String, nullable=False)
    source_interface = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    enabled = Column(Boolean, default=True)
    autonomous_system_id = Column(Integer, ForeignKey("autonomous_systems.id"), nullable=False)
    import_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    export_policy_id = Column(Integer, ForeignKey("routing_policies.id"), nullable=True)
    hold_time = Column(Integer, default=180)  # BGP hold timer
    keepalive = Column(Integer, default=60)  # BGP keepalive timer
    remote_endpoint_id = Column(Integer, ForeignKey("peer_endpoints.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    device = relationship("Device", backref="peer_endpoints")
    routing_instance = relationship("RoutingInstance", backref="peer_endpoints")
    peer_group = relationship("PeerGroup", backref="peer_endpoints")
    autonomous_system = relationship("AutonomousSystem", backref="peer_endpoints")
    import_policy = relationship("RoutingPolicy", foreign_keys=[import_policy_id], backref="peer_endpoints_import")
    export_policy = relationship("RoutingPolicy", foreign_keys=[export_policy_id], backref="peer_endpoints_export")
    remote_endpoint = relationship("PeerEndpoint", remote_side=[id], backref="local_endpoints")


class PeeringRole(Base):
    __tablename__ = "peering_roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    slug = Column(String, unique=True, index=True, nullable=False)
    color = Column(String, default="#9e9e9e")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Many-to-many relationships
    peerings = relationship("BGPPeering", secondary="peering_tags", back_populates="tags")
    peer_groups = relationship("PeerGroup", secondary="peer_group_tags", back_populates="tags")
    autonomous_systems = relationship("AutonomousSystem", secondary="as_tags", back_populates="tags")


# Association tables for many-to-many relationships
peering_tags = Table(
    "peering_tags",
    Base.metadata,
    Column("peering_id", Integer, ForeignKey("bgp_peerings.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

peer_group_tags = Table(
    "peer_group_tags",
    Base.metadata,
    Column("peer_group_id", Integer, ForeignKey("peer_groups.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)

as_tags = Table(
    "as_tags",
    Base.metadata,
    Column("autonomous_system_id", Integer, ForeignKey("autonomous_systems.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)


class AddressFamily(Base):
    __tablename__ = "address_families"
    
    id = Column(Integer, primary_key=True, index=True)
    routing_instance_id = Column(Integer, ForeignKey("routing_instances.id"), nullable=False)
    afi = Column(String, nullable=False)  # ipv4, ipv6, etc.
    safi = Column(String, nullable=False)  # unicast, multicast, etc.
    enabled = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    routing_instance = relationship("RoutingInstance", backref="address_families")


class RoutingPolicy(Base):
    __tablename__ = "routing_policies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=False)  # import, export, or both
    rules = Column(JSON, nullable=True)  # Structured policy rules
    priority = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Secret(Base):
    __tablename__ = "secrets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    type = Column(String, nullable=False)  # md5, tcp_ao
    secret_value = Column(Text, nullable=False)  # Should be encrypted in production
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to peer endpoints
    peer_endpoint_id = Column(Integer, ForeignKey("peer_endpoints.id"), nullable=True)
    peer_endpoint = relationship("PeerEndpoint", backref="secrets")


class BGPSessionState(Base):
    __tablename__ = "bgp_session_states"
    
    id = Column(Integer, primary_key=True, index=True)
    peering_id = Column(Integer, ForeignKey("bgp_peerings.id"), nullable=False)
    state = Column(String, nullable=False, default="idle")
    last_state_change = Column(DateTime, default=datetime.utcnow)
    uptime_seconds = Column(Integer, default=0)
    prefixes_received = Column(Integer, default=0)
    prefixes_advertised = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    peering = relationship("BGPPeering", backref="session_state")


class ChangeLog(Base):
    __tablename__ = "change_log"
    
    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)  # Created, Modified, Deleted
    object_type = Column(String, nullable=False)  # BGP Peering, Peer Group, etc.
    object_id = Column(Integer, nullable=False)
    object_name = Column(String, nullable=False)
    user = Column(String, nullable=False)
    changes = Column(JSON, nullable=True)  # Field-level changes
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class BGPPeering(Base):
    __tablename__ = "bgp_peerings"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("peering_roles.id"), nullable=True)
    status = Column(String, default="Active")
    endpoint_a_id = Column(Integer, ForeignKey("peer_endpoints.id"), nullable=False)
    endpoint_z_id = Column(Integer, ForeignKey("peer_endpoints.id"), nullable=False)
    state = Column(String, default="idle")  # Session state
    last_state_change = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    role = relationship("PeeringRole", backref="peerings")
    endpoint_a = relationship("PeerEndpoint", foreign_keys=[endpoint_a_id], backref="peerings_as_a")
    endpoint_z = relationship("PeerEndpoint", foreign_keys=[endpoint_z_id], backref="peerings_as_z")
    tags = relationship("Tag", secondary="peering_tags", back_populates="peerings")
