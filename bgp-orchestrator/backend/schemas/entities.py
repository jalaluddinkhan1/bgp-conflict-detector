"""
Pydantic schemas for BGP-related entities.
"""
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, IPvAnyAddress, field_validator


# Tag Schemas
class TagBase(BaseModel):
    """Base schema for Tag."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    color: str = Field(default="#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str | None = None

    @field_validator("slug")
    @classmethod
    def generate_slug(cls, v: str | None, info) -> str:
        """Generate slug from name if not provided."""
        if v is None and "name" in info.data:
            name = info.data["name"]
            slug = name.lower().replace(" ", "-").replace("_", "-")
            # Remove special characters
            slug = "".join(c if c.isalnum() or c == "-" else "" for c in slug)
            return slug
        return v


class TagCreate(TagBase):
    """Schema for creating a Tag."""
    pass


class TagUpdate(BaseModel):
    """Schema for updating a Tag."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    description: str | None = None


class TagResponse(TagBase):
    """Schema for Tag response."""
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# Autonomous System Schemas
class AutonomousSystemBase(BaseModel):
    """Base schema for Autonomous System."""
    asn: int = Field(..., ge=1, le=4294967295)
    description: str | None = None
    status: str = Field(default="active", pattern="^(active|inactive|reserved)$")
    rir: str | None = Field(default=None, max_length=10)


class AutonomousSystemCreate(AutonomousSystemBase):
    """Schema for creating an Autonomous System."""
    pass


class AutonomousSystemUpdate(BaseModel):
    """Schema for updating an Autonomous System."""
    asn: int | None = Field(default=None, ge=1, le=4294967295)
    description: str | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|reserved)$")
    rir: str | None = Field(default=None, max_length=10)


class AutonomousSystemResponse(AutonomousSystemBase):
    """Schema for Autonomous System response."""
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    tags: list[TagResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# Peer Group Schemas
class PeerGroupBase(BaseModel):
    """Base schema for Peer Group."""
    name: str = Field(..., min_length=1, max_length=255)
    device_id: int | None = None
    description: str | None = None
    enabled: bool = Field(default=True)
    autonomous_system_id: int | None = None
    import_policy_id: int | None = None
    export_policy_id: int | None = None
    source_ip_address: str | None = Field(default=None, max_length=45)
    source_interface: str | None = Field(default=None, max_length=255)
    template_id: int | None = None


class PeerGroupCreate(PeerGroupBase):
    """Schema for creating a Peer Group."""
    pass


class PeerGroupUpdate(BaseModel):
    """Schema for updating a Peer Group."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    device_id: int | None = None
    description: str | None = None
    enabled: bool | None = None
    autonomous_system_id: int | None = None
    import_policy_id: int | None = None
    export_policy_id: int | None = None
    source_ip_address: str | None = Field(default=None, max_length=45)
    source_interface: str | None = Field(default=None, max_length=255)
    template_id: int | None = None


class PeerGroupResponse(PeerGroupBase):
    """Schema for Peer Group response."""
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    tags: list[TagResponse] = Field(default_factory=list)
    autonomous_system: AutonomousSystemResponse | None = None
    import_policy: "RoutingPolicyResponse | None" = None
    export_policy: "RoutingPolicyResponse | None" = None

    model_config = {"from_attributes": True}


# Peer Endpoint Schemas
class PeerEndpointBase(BaseModel):
    """Base schema for Peer Endpoint."""
    name: str = Field(..., min_length=1, max_length=255)
    device_id: int | None = None
    routing_instance_id: int | None = None
    peer_group_id: int | None = None
    source_ip_address: IPvAnyAddress
    source_interface: str | None = Field(default=None, max_length=255)
    description: str | None = None
    enabled: bool = Field(default=True)
    autonomous_system_id: int = Field(...)
    import_policy_id: int | None = None
    export_policy_id: int | None = None
    hold_time: int | None = Field(default=None, ge=3, le=65535)
    keepalive: int | None = Field(default=None, ge=1, le=65535)
    remote_endpoint_id: int | None = None


class PeerEndpointCreate(PeerEndpointBase):
    """Schema for creating a Peer Endpoint."""
    pass


class PeerEndpointUpdate(BaseModel):
    """Schema for updating a Peer Endpoint."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    device_id: int | None = None
    routing_instance_id: int | None = None
    peer_group_id: int | None = None
    source_ip_address: IPvAnyAddress | None = None
    source_interface: str | None = Field(default=None, max_length=255)
    description: str | None = None
    enabled: bool | None = None
    autonomous_system_id: int | None = None
    import_policy_id: int | None = None
    export_policy_id: int | None = None
    hold_time: int | None = Field(default=None, ge=3, le=65535)
    keepalive: int | None = Field(default=None, ge=1, le=65535)
    remote_endpoint_id: int | None = None


class PeerEndpointResponse(PeerEndpointBase):
    """Schema for Peer Endpoint response."""
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    tags: list[TagResponse] = Field(default_factory=list)
    autonomous_system: AutonomousSystemResponse | None = None
    import_policy: "RoutingPolicyResponse | None" = None
    export_policy: "RoutingPolicyResponse | None" = None

    model_config = {"from_attributes": True}


# Routing Policy Schemas
class RoutingPolicyBase(BaseModel):
    """Base schema for Routing Policy."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    type: str = Field(default="standard")
    rules: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=1, le=1000)


class RoutingPolicyCreate(RoutingPolicyBase):
    """Schema for creating a Routing Policy."""
    pass


class RoutingPolicyUpdate(BaseModel):
    """Schema for updating a Routing Policy."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    type: str | None = None
    rules: dict[str, Any] | None = None
    priority: int | None = Field(default=None, ge=1, le=1000)


class RoutingPolicyResponse(RoutingPolicyBase):
    """Schema for Routing Policy response."""
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


# Address Family Schemas
class AddressFamilyBase(BaseModel):
    """Base schema for Address Family."""
    routing_instance_id: int = Field(...)
    afi: str = Field(..., pattern="^(ipv4|ipv6)$")
    safi: str = Field(..., pattern="^(unicast|multicast|vpnv4|l2vpn-evpn)$")
    enabled: bool = Field(default=True)
    description: str | None = None


class AddressFamilyCreate(AddressFamilyBase):
    """Schema for creating an Address Family."""
    pass


class AddressFamilyUpdate(BaseModel):
    """Schema for updating an Address Family."""
    routing_instance_id: int | None = None
    afi: str | None = Field(default=None, pattern="^(ipv4|ipv6)$")
    safi: str | None = Field(default=None, pattern="^(unicast|multicast|vpnv4|l2vpn-evpn)$")
    enabled: bool | None = None
    description: str | None = None


class AddressFamilyResponse(AddressFamilyBase):
    """Schema for Address Family response."""
    id: int
    created_at: datetime
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}

