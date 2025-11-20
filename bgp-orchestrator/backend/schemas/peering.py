"""
Pydantic schemas for BGP peering management.
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, IPvAnyAddress, model_validator


class PeeringStatus(str, Enum):
    """BGP peering status values."""

    ACTIVE = "active"
    PENDING = "pending"
    DISABLED = "disabled"


class AddressFamily(str, Enum):
    """Supported BGP address families."""

    IPV4 = "ipv4"
    IPV6 = "ipv6"
    VPNV4 = "vpnv4"
    L2VPN_EVPN = "l2vpn-evpn"


class BGPPeeringBase(BaseModel):
    """Base schema with common fields for BGP peering."""

    name: str = Field(..., min_length=1, max_length=255, description="Peering session name")
    local_asn: int = Field(..., ge=1, le=4294967295, description="Local ASN")
    peer_asn: int = Field(..., ge=1, le=4294967295, description="Peer ASN")
    peer_ip: IPvAnyAddress = Field(..., description="Peer IP address (IPv4 or IPv6)")
    hold_time: int = Field(..., ge=3, le=65535, description="BGP hold time in seconds")
    keepalive: int = Field(..., ge=1, le=65535, description="BGP keepalive interval in seconds")
    device: str = Field(..., min_length=1, max_length=255, description="Device/router name")
    interface: str | None = Field(default=None, max_length=255, description="Interface name")
    status: PeeringStatus = Field(default=PeeringStatus.PENDING, description="Peering status")
    address_families: list[AddressFamily] = Field(
        default_factory=lambda: [AddressFamily.IPV4],
        description="Supported address families",
    )
    routing_policy: dict[str, Any] = Field(
        default_factory=dict,
        description="Routing policy configuration (import/export policies, communities, etc.)",
    )

    @model_validator(mode="after")
    def validate_keepalive_against_hold_time(self) -> "BGPPeeringBase":
        """Validate keepalive is less than or equal to one-third of hold_time."""
        if self.keepalive > self.hold_time / 3:
            raise ValueError(
                f"keepalive ({self.keepalive}) must be less than or equal to one-third of hold_time ({self.hold_time})"
            )
        return self

    @field_validator("local_asn", "peer_asn")
    @classmethod
    def validate_asn(cls, v: int) -> int:
        """Validate ASN is within valid ranges (private ASNs: 64512-65534, 4200000000-4294967294)."""
        if 64512 <= v <= 65534 or 4200000000 <= v <= 4294967294:
            # Private ASN range - warn but allow
            pass
        elif not (1 <= v <= 4294967295):
            raise ValueError("ASN must be between 1 and 4294967295")
        return v

    @field_validator("address_families")
    @classmethod
    def validate_address_families(cls, v: list[AddressFamily]) -> list[AddressFamily]:
        """Ensure at least one address family is specified."""
        if not v:
            raise ValueError("At least one address family must be specified")
        return v


class BGPPeeringCreate(BGPPeeringBase):
    """Schema for creating a new BGP peering session."""

    pass


class BGPPeeringUpdate(BaseModel):
    """Schema for updating an existing BGP peering session."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    local_asn: int | None = Field(default=None, ge=1, le=4294967295)
    peer_asn: int | None = Field(default=None, ge=1, le=4294967295)
    peer_ip: IPvAnyAddress | None = None
    hold_time: int | None = Field(default=None, ge=3, le=65535)
    keepalive: int | None = Field(default=None, ge=1, le=65535)
    device: str | None = Field(default=None, min_length=1, max_length=255)
    interface: str | None = Field(default=None, max_length=255)
    status: PeeringStatus | None = None
    address_families: list[AddressFamily] | None = None
    routing_policy: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_keepalive_update(self) -> "BGPPeeringUpdate":
        """Validate keepalive against hold_time if both are provided."""
        if self.keepalive is not None and self.hold_time is not None:
            if self.keepalive > self.hold_time / 3:
                raise ValueError(
                    f"keepalive ({self.keepalive}) must be less than or equal to one-third of hold_time ({self.hold_time})"
                )
        return self


class BGPPeeringResponse(BGPPeeringBase):
    """Schema for BGP peering response with additional metadata."""

    id: int = Field(..., description="Unique peering session ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime | None = Field(default=None, description="Last update timestamp")
    created_by: str | None = Field(default=None, description="User who created the peering session")
    updated_by: str | None = Field(default=None, description="User who last updated the peering session")

    model_config = {"from_attributes": True}

