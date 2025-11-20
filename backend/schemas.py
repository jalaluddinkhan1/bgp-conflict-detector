from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class DeviceBase(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "Active"


class DeviceCreate(DeviceBase):
    pass


class Device(DeviceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AutonomousSystemBase(BaseModel):
    asn: int
    description: Optional[str] = None
    status: str = "Active"


class AutonomousSystemCreate(AutonomousSystemBase):
    pass


class AutonomousSystem(AutonomousSystemBase):
    id: int
    created_at: datetime
    updated_at: datetime
    rir: Optional[str] = None
    tags: List["Tag"] = []
    
    class Config:
        from_attributes = True


class RoutingInstanceBase(BaseModel):
    device_id: int
    autonomous_system_id: int
    name: str
    description: Optional[str] = None


class RoutingInstanceCreate(RoutingInstanceBase):
    pass


class RoutingInstance(RoutingInstanceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    device: Optional[Device] = None
    autonomous_system: Optional[AutonomousSystem] = None
    name: Optional[str] = None
    
    class Config:
        from_attributes = True


class PeerGroupTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None


class PeerGroupTemplateCreate(PeerGroupTemplateBase):
    pass


class PeerGroupTemplate(PeerGroupTemplateBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PeerGroupBase(BaseModel):
    name: str
    device_id: int
    routing_instance_id: int
    template_id: Optional[int] = None
    source_ip_address: Optional[str] = None
    source_interface: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    autonomous_system_id: Optional[int] = None
    import_policy: Optional[str] = None
    export_policy: Optional[str] = None


class PeerGroupCreate(PeerGroupBase):
    pass


class PeerGroup(PeerGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    device: Optional[Device] = None
    routing_instance: Optional[RoutingInstance] = None
    autonomous_system: Optional[AutonomousSystem] = None
    template: Optional[PeerGroupTemplate] = None
    import_policy_id: Optional[int] = None
    export_policy_id: Optional[int] = None
    import_policy: Optional["RoutingPolicy"] = None
    export_policy: Optional["RoutingPolicy"] = None
    tags: List["Tag"] = []
    
    class Config:
        from_attributes = True


class PeerEndpointBase(BaseModel):
    name: str
    device_id: int
    routing_instance_id: int
    peer_group_id: Optional[int] = None
    source_ip_address: str
    source_interface: Optional[str] = None
    description: Optional[str] = None
    enabled: bool = True
    autonomous_system_id: int
    import_policy: Optional[str] = None
    export_policy: Optional[str] = None


class PeerEndpointCreate(PeerEndpointBase):
    pass


class PeerEndpoint(PeerEndpointBase):
    id: int
    created_at: datetime
    updated_at: datetime
    device: Optional[Device] = None
    routing_instance: Optional[RoutingInstance] = None
    autonomous_system: Optional[AutonomousSystem] = None
    peer_group: Optional[PeerGroup] = None
    import_policy_id: Optional[int] = None
    export_policy_id: Optional[int] = None
    import_policy: Optional["RoutingPolicy"] = None
    export_policy: Optional["RoutingPolicy"] = None
    hold_time: Optional[int] = None
    keepalive: Optional[int] = None
    remote_endpoint_id: Optional[int] = None
    
    class Config:
        from_attributes = True


class PeeringRoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class PeeringRoleCreate(PeeringRoleBase):
    pass


class PeeringRole(PeeringRoleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BGPPeeringBase(BaseModel):
    name: str
    role_id: Optional[int] = None
    status: str = "Active"
    endpoint_a_id: int
    endpoint_z_id: int


class BGPPeeringCreate(BGPPeeringBase):
    pass


class BGPPeering(BGPPeeringBase):
    id: int
    created_at: datetime
    updated_at: datetime
    role: Optional[PeeringRole] = None
    endpoint_a: Optional[PeerEndpoint] = None
    endpoint_z: Optional[PeerEndpoint] = None
    state: Optional[str] = None
    last_state_change: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TagBase(BaseModel):
    name: str
    slug: str
    color: str = "#9e9e9e"
    description: Optional[str] = None


class TagCreate(TagBase):
    pass


class Tag(TagBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class AddressFamilyBase(BaseModel):
    routing_instance_id: int
    afi: str
    safi: str
    enabled: bool = True
    description: Optional[str] = None


class AddressFamilyCreate(AddressFamilyBase):
    pass


class AddressFamily(AddressFamilyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    routing_instance: Optional[RoutingInstance] = None
    
    class Config:
        from_attributes = True


class RoutingPolicyBase(BaseModel):
    name: str
    description: Optional[str] = None
    type: str  # import, export, both
    rules: Optional[dict] = None
    priority: int = 100


class RoutingPolicyCreate(RoutingPolicyBase):
    pass


class RoutingPolicy(RoutingPolicyBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SecretBase(BaseModel):
    name: str
    type: str  # md5, tcp_ao
    secret_value: str
    description: Optional[str] = None
    peer_endpoint_id: Optional[int] = None


class SecretCreate(SecretBase):
    pass


class Secret(SecretBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BGPSessionStateBase(BaseModel):
    peering_id: int
    state: str = "idle"
    last_state_change: Optional[datetime] = None
    uptime_seconds: int = 0
    prefixes_received: int = 0
    prefixes_advertised: int = 0
    error_message: Optional[str] = None


class BGPSessionStateCreate(BGPSessionStateBase):
    pass


class BGPSessionState(BGPSessionStateBase):
    id: int
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ChangeLogEntry(BaseModel):
    id: int
    action: str
    object_type: str
    object_id: int
    object_name: str
    user: str
    changes: Optional[dict] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True
