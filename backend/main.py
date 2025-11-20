from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db, init_db
from validators import (
    validate_asn, validate_ip_address, validate_peering_name,
    validate_endpoint_relationship, validate_bgp_state,
    validate_afi_safi, validate_hold_time, validate_keepalive
)
from models import (
    Device, AutonomousSystem, RoutingInstance, PeerGroupTemplate,
    PeerGroup, PeerEndpoint, PeeringRole, BGPPeering,
    Tag, AddressFamily, RoutingPolicy, Secret, BGPSessionState, ChangeLog
)
from sqlalchemy.orm import joinedload
from schemas import (
    Device as DeviceSchema, DeviceCreate,
    AutonomousSystem as ASSchema, AutonomousSystemCreate,
    RoutingInstance as RISchema, RoutingInstanceCreate,
    PeerGroupTemplate as PGTemplateSchema, PeerGroupTemplateCreate,
    PeerGroup as PGSchema, PeerGroupCreate,
    PeerEndpoint as PESchema, PeerEndpointCreate,
    PeeringRole as RoleSchema, PeeringRoleCreate,
    BGPPeering as PeeringSchema, BGPPeeringCreate,
    Tag as TagSchema, TagCreate,
    AddressFamily as AddressFamilySchema, AddressFamilyCreate,
    RoutingPolicy as RoutingPolicySchema, RoutingPolicyCreate,
    Secret as SecretSchema, SecretCreate,
    BGPSessionState as SessionStateSchema, BGPSessionStateCreate,
    ChangeLogEntry
)

app = FastAPI(title="Nautobot BGP API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()


# Dashboard Stats
@app.get("/api/dashboard/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    return {
        "sites": 3,
        "tenants": 0,
        "racks": 1,
        "vrfs": 1,
        "clusters": 0,
        "virtual_machines": 0,
        "git_repositories": 2,
    }


# Devices
@app.get("/api/devices", response_model=List[DeviceSchema])
async def get_devices(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Device).offset(skip).limit(limit).all()


@app.get("/api/devices/{device_id}", response_model=DeviceSchema)
async def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


# Autonomous Systems
@app.get("/api/autonomous-systems", response_model=List[ASSchema])
async def get_autonomous_systems(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(AutonomousSystem).offset(skip).limit(limit).all()


@app.get("/api/autonomous-systems/{as_id}", response_model=ASSchema)
async def get_autonomous_system(as_id: int, db: Session = Depends(get_db)):
    as_obj = db.query(AutonomousSystem).filter(AutonomousSystem.id == as_id).first()
    if not as_obj:
        raise HTTPException(status_code=404, detail="Autonomous System not found")
    # Load tags using the association table
    from models import as_tags
    tag_ids = db.query(as_tags.c.tag_id).filter(as_tags.c.autonomous_system_id == as_id).all()
    if tag_ids:
        as_obj.tags = db.query(Tag).filter(Tag.id.in_([t[0] for t in tag_ids])).all()
    else:
        as_obj.tags = []
    return as_obj


@app.post("/api/autonomous-systems", response_model=ASSchema)
async def create_autonomous_system(as_data: AutonomousSystemCreate, db: Session = Depends(get_db)):
    if not validate_asn(as_data.asn):
        raise HTTPException(status_code=400, detail="Invalid ASN. Must be between 1 and 4294967295")
    
    db_as = AutonomousSystem(**as_data.model_dump())
    db.add(db_as)
    db.commit()
    db.refresh(db_as)
    return db_as


# BGP Peerings
@app.get("/api/bgp-peerings", response_model=List[PeeringSchema])
async def get_bgp_peerings(
    skip: int = 0,
    limit: int = 50,
    role: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    device: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(BGPPeering)
    
    if role:
        query = query.join(PeeringRole).filter(PeeringRole.name == role)
    if status:
        query = query.filter(BGPPeering.status == status)
    if state:
        query = query.filter(BGPPeering.state == state)
    if device:
        query = query.join(PeerEndpoint, BGPPeering.endpoint_a_id == PeerEndpoint.id).filter(
            PeerEndpoint.name.ilike(f"%{device}%")
        )
    if tag:
        from models import peering_tags
        tag_obj = db.query(Tag).filter(Tag.slug == tag).first()
        if tag_obj:
            peering_ids = db.query(peering_tags.c.peering_id).filter(peering_tags.c.tag_id == tag_obj.id).all()
            query = query.filter(BGPPeering.id.in_([p[0] for p in peering_ids]))
    if search:
        query = query.filter(BGPPeering.name.ilike(f"%{search}%"))
    
    total = query.count()
    peerings = query.offset(skip).limit(limit).all()
    
    # Load relationships for each peering
    for peering in peerings:
        if peering.endpoint_a:
            peering.endpoint_a.device = db.query(Device).filter(Device.id == peering.endpoint_a.device_id).first()
        if peering.endpoint_z:
            peering.endpoint_z.device = db.query(Device).filter(Device.id == peering.endpoint_z.device_id).first()
        # Load tags
        from models import peering_tags
        tag_ids = db.query(peering_tags.c.tag_id).filter(peering_tags.c.peering_id == peering.id).all()
        if tag_ids:
            peering.tags = db.query(Tag).filter(Tag.id.in_([t[0] for t in tag_ids])).all()
        else:
            peering.tags = []
    
    # Return as list for backwards compatibility if no pagination requested
    if skip == 0 and limit == 50 and not any([role, status, state, device, tag, search]):
        return peerings
    
    # Always return paginated response for consistency
    return {"items": peerings, "total": total, "skip": skip, "limit": limit}


@app.get("/api/bgp-peerings/{peering_id}", response_model=PeeringSchema)
async def get_bgp_peering(peering_id: int, db: Session = Depends(get_db)):
    peering = db.query(BGPPeering).filter(BGPPeering.id == peering_id).first()
    if not peering:
        raise HTTPException(status_code=404, detail="BGP Peering not found")
    # Load relationships
    if peering.endpoint_a:
        peering.endpoint_a.device = db.query(Device).filter(Device.id == peering.endpoint_a.device_id).first()
        peering.endpoint_a.autonomous_system = db.query(AutonomousSystem).filter(AutonomousSystem.id == peering.endpoint_a.autonomous_system_id).first()
        if peering.endpoint_a.import_policy_id:
            peering.endpoint_a.import_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == peering.endpoint_a.import_policy_id).first()
        if peering.endpoint_a.export_policy_id:
            peering.endpoint_a.export_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == peering.endpoint_a.export_policy_id).first()
    if peering.endpoint_z:
        peering.endpoint_z.device = db.query(Device).filter(Device.id == peering.endpoint_z.device_id).first()
        peering.endpoint_z.autonomous_system = db.query(AutonomousSystem).filter(AutonomousSystem.id == peering.endpoint_z.autonomous_system_id).first()
        if peering.endpoint_z.import_policy_id:
            peering.endpoint_z.import_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == peering.endpoint_z.import_policy_id).first()
        if peering.endpoint_z.export_policy_id:
            peering.endpoint_z.export_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == peering.endpoint_z.export_policy_id).first()
    
    # Load session state if exists
    session_state = db.query(BGPSessionState).filter(BGPSessionState.peering_id == peering_id).first()
    if session_state:
        peering.state = session_state.state
        peering.last_state_change = session_state.last_state_change
    
    # Load tags using the association table
    from models import peering_tags
    tag_ids = db.query(peering_tags.c.tag_id).filter(peering_tags.c.peering_id == peering_id).all()
    if tag_ids:
        peering.tags = db.query(Tag).filter(Tag.id.in_([t[0] for t in tag_ids])).all()
    else:
        peering.tags = []
    
    return peering


@app.post("/api/bgp-peerings", response_model=PeeringSchema)
async def create_bgp_peering(peering_data: BGPPeeringCreate, db: Session = Depends(get_db)):
    # Validate peering name uniqueness
    if not validate_peering_name(peering_data.name, db):
        raise HTTPException(status_code=400, detail="Peering name already exists")
    
    # Validate endpoint relationship
    valid, error_msg = validate_endpoint_relationship(
        peering_data.endpoint_a_id, 
        peering_data.endpoint_z_id, 
        db
    )
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    db_peering = BGPPeering(**peering_data.model_dump())
    db.add(db_peering)
    db.commit()
    db.refresh(db_peering)
    return db_peering


@app.delete("/api/bgp-peerings/{peering_id}")
async def delete_bgp_peering(peering_id: int, db: Session = Depends(get_db)):
    peering = db.query(BGPPeering).filter(BGPPeering.id == peering_id).first()
    if not peering:
        raise HTTPException(status_code=404, detail="BGP Peering not found")
    db.delete(peering)
    db.commit()
    return {"message": "BGP Peering deleted successfully"}


@app.post("/api/bgp-peerings/bulk-delete")
async def bulk_delete_peerings(peering_ids: List[int], db: Session = Depends(get_db)):
    deleted = db.query(BGPPeering).filter(BGPPeering.id.in_(peering_ids)).delete(synchronize_session=False)
    db.commit()
    return {"message": f"Deleted {deleted} peerings", "deleted_count": deleted}


@app.put("/api/bgp-peerings/bulk-update")
async def bulk_update_peerings(
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    peering_ids = data.get("peering_ids", [])
    updates = data.get("updates", {})
    
    allowed_fields = ["status", "role_id", "state"]
    update_dict = {k: v for k, v in updates.items() if k in allowed_fields}
    
    updated = db.query(BGPPeering).filter(BGPPeering.id.in_(peering_ids)).update(
        update_dict, synchronize_session=False
    )
    db.commit()
    return {"message": f"Updated {updated} peerings", "updated_count": updated}


# Peer Groups
@app.get("/api/peer-groups", response_model=List[PGSchema])
async def get_peer_groups(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(PeerGroup).offset(skip).limit(limit).all()


@app.get("/api/peer-groups/{group_id}", response_model=PGSchema)
async def get_peer_group(group_id: int, db: Session = Depends(get_db)):
    group = db.query(PeerGroup).filter(PeerGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Peer Group not found")
    # Load relationships
    if group.device_id:
        group.device = db.query(Device).filter(Device.id == group.device_id).first()
    if group.autonomous_system_id:
        group.autonomous_system = db.query(AutonomousSystem).filter(AutonomousSystem.id == group.autonomous_system_id).first()
    if group.routing_instance_id:
        group.routing_instance = db.query(RoutingInstance).filter(RoutingInstance.id == group.routing_instance_id).first()
    if group.import_policy_id:
        group.import_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == group.import_policy_id).first()
    if group.export_policy_id:
        group.export_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == group.export_policy_id).first()
    # Load tags using the association table
    from models import peer_group_tags
    tag_ids = db.query(peer_group_tags.c.tag_id).filter(peer_group_tags.c.peer_group_id == group_id).all()
    if tag_ids:
        group.tags = db.query(Tag).filter(Tag.id.in_([t[0] for t in tag_ids])).all()
    else:
        group.tags = []
    return group


@app.post("/api/peer-groups", response_model=PGSchema)
async def create_peer_group(group_data: PeerGroupCreate, db: Session = Depends(get_db)):
    db_group = PeerGroup(**group_data.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


# Peer Endpoints
@app.get("/api/peer-endpoints", response_model=List[PESchema])
async def get_peer_endpoints(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(PeerEndpoint).offset(skip).limit(limit).all()


@app.get("/api/peer-endpoints/{endpoint_id}", response_model=PESchema)
async def get_peer_endpoint(endpoint_id: int, db: Session = Depends(get_db)):
    endpoint = db.query(PeerEndpoint).filter(PeerEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Peer Endpoint not found")
    # Load relationships
    if endpoint.device_id:
        endpoint.device = db.query(Device).filter(Device.id == endpoint.device_id).first()
    if endpoint.autonomous_system_id:
        endpoint.autonomous_system = db.query(AutonomousSystem).filter(AutonomousSystem.id == endpoint.autonomous_system_id).first()
    if endpoint.routing_instance_id:
        endpoint.routing_instance = db.query(RoutingInstance).filter(RoutingInstance.id == endpoint.routing_instance_id).first()
    if endpoint.import_policy_id:
        endpoint.import_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == endpoint.import_policy_id).first()
    if endpoint.export_policy_id:
        endpoint.export_policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == endpoint.export_policy_id).first()
    return endpoint


@app.post("/api/peer-endpoints", response_model=PESchema)
async def create_peer_endpoint(endpoint_data: PeerEndpointCreate, db: Session = Depends(get_db)):
    # Validate IP address
    if not validate_ip_address(endpoint_data.source_ip_address):
        raise HTTPException(status_code=400, detail="Invalid IP address format")
    
    # Validate hold time if provided
    if hasattr(endpoint_data, 'hold_time') and endpoint_data.hold_time:
        if not validate_hold_time(endpoint_data.hold_time):
            raise HTTPException(status_code=400, detail="Invalid hold time. Must be 0 or between 3 and 65535")
    
    # Validate keepalive if provided
    if hasattr(endpoint_data, 'keepalive') and hasattr(endpoint_data, 'hold_time'):
        valid, error_msg = validate_keepalive(endpoint_data.keepalive or 60, endpoint_data.hold_time or 180)
        if not valid:
            raise HTTPException(status_code=400, detail=error_msg)
    
    db_endpoint = PeerEndpoint(**endpoint_data.model_dump())
    db.add(db_endpoint)
    db.commit()
    db.refresh(db_endpoint)
    return db_endpoint


# Peering Roles
@app.get("/api/peering-roles", response_model=List[RoleSchema])
async def get_peering_roles(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(PeeringRole).offset(skip).limit(limit).all()


@app.get("/api/peering-roles/{role_id}", response_model=RoleSchema)
async def get_peering_role(role_id: int, db: Session = Depends(get_db)):
    role = db.query(PeeringRole).filter(PeeringRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Peering Role not found")
    return role


# Address Families
@app.get("/api/address-families", response_model=List[AddressFamilySchema])
async def get_address_families(skip: int = 0, limit: int = 100, routing_instance_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(AddressFamily)
    if routing_instance_id:
        query = query.filter(AddressFamily.routing_instance_id == routing_instance_id)
    return query.offset(skip).limit(limit).all()


@app.get("/api/address-families/{af_id}", response_model=AddressFamilySchema)
async def get_address_family(af_id: int, db: Session = Depends(get_db)):
    af = db.query(AddressFamily).filter(AddressFamily.id == af_id).first()
    if not af:
        raise HTTPException(status_code=404, detail="Address Family not found")
    return af


@app.post("/api/address-families", response_model=AddressFamilySchema)
async def create_address_family(af_data: AddressFamilyCreate, db: Session = Depends(get_db)):
    valid, error_msg = validate_afi_safi(af_data.afi, af_data.safi)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    db_af = AddressFamily(**af_data.model_dump())
    db.add(db_af)
    db.commit()
    db.refresh(db_af)
    return db_af


# Routing Policies
@app.get("/api/routing-policies", response_model=List[RoutingPolicySchema])
async def get_routing_policies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(RoutingPolicy).offset(skip).limit(limit).all()


@app.get("/api/routing-policies/{policy_id}", response_model=RoutingPolicySchema)
async def get_routing_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(RoutingPolicy).filter(RoutingPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Routing Policy not found")
    return policy


@app.post("/api/routing-policies", response_model=RoutingPolicySchema)
async def create_routing_policy(policy_data: RoutingPolicyCreate, db: Session = Depends(get_db)):
    db_policy = RoutingPolicy(**policy_data.model_dump())
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


# Tags
@app.get("/api/tags", response_model=List[TagSchema])
async def get_tags(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Tag).offset(skip).limit(limit).all()


@app.get("/api/tags/{tag_id}", response_model=TagSchema)
async def get_tag(tag_id: int, db: Session = Depends(get_db)):
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@app.post("/api/tags", response_model=TagSchema)
async def create_tag(tag_data: TagCreate, db: Session = Depends(get_db)):
    db_tag = Tag(**tag_data.model_dump())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


# Secrets
@app.get("/api/secrets", response_model=List[SecretSchema])
async def get_secrets(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(Secret).offset(skip).limit(limit).all()


@app.get("/api/secrets/{secret_id}", response_model=SecretSchema)
async def get_secret(secret_id: int, db: Session = Depends(get_db)):
    secret = db.query(Secret).filter(Secret.id == secret_id).first()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return secret


@app.post("/api/secrets", response_model=SecretSchema)
async def create_secret(secret_data: SecretCreate, db: Session = Depends(get_db)):
    db_secret = Secret(**secret_data.model_dump())
    db.add(db_secret)
    db.commit()
    db.refresh(db_secret)
    return db_secret


# BGP Session States
@app.get("/api/bgp-session-states", response_model=List[SessionStateSchema])
async def get_session_states(skip: int = 0, limit: int = 100, peering_id: Optional[int] = Query(None), db: Session = Depends(get_db)):
    query = db.query(BGPSessionState)
    if peering_id:
        query = query.filter(BGPSessionState.peering_id == peering_id)
    return query.offset(skip).limit(limit).all()


@app.get("/api/bgp-session-states/{state_id}", response_model=SessionStateSchema)
async def get_session_state(state_id: int, db: Session = Depends(get_db)):
    state = db.query(BGPSessionState).filter(BGPSessionState.id == state_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="Session State not found")
    return state


@app.post("/api/bgp-session-states", response_model=SessionStateSchema)
async def create_session_state(state_data: BGPSessionStateCreate, db: Session = Depends(get_db)):
    db_state = BGPSessionState(**state_data.model_dump())
    db.add(db_state)
    db.commit()
    db.refresh(db_state)
    return db_state


@app.put("/api/bgp-session-states/{state_id}", response_model=SessionStateSchema)
async def update_session_state(state_id: int, state_data: BGPSessionStateCreate, db: Session = Depends(get_db)):
    if state_data.state and not validate_bgp_state(state_data.state):
        raise HTTPException(status_code=400, detail="Invalid BGP state")
    
    state = db.query(BGPSessionState).filter(BGPSessionState.id == state_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="Session State not found")
    for key, value in state_data.model_dump().items():
        setattr(state, key, value)
    db.commit()
    db.refresh(state)
    return state


# Change Log
@app.get("/api/change-log", response_model=List[ChangeLogEntry])
async def get_change_log(
    skip: int = 0,
    limit: int = 50,
    object_type: Optional[str] = Query(None),
    user: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ChangeLog)
    if object_type:
        query = query.filter(ChangeLog.object_type == object_type)
    if user:
        query = query.filter(ChangeLog.user == user)
    query = query.order_by(ChangeLog.timestamp.desc())
    return query.offset(skip).limit(limit).all()


@app.get("/api/change-log/{object_type}/{object_id}", response_model=List[ChangeLogEntry])
async def get_object_change_log(object_type: str, object_id: int, db: Session = Depends(get_db)):
    logs = db.query(ChangeLog).filter(
        ChangeLog.object_type == object_type,
        ChangeLog.object_id == object_id
    ).order_by(ChangeLog.timestamp.desc()).all()
    return logs


# Export endpoints
@app.get("/api/bgp-peerings/export/csv")
async def export_peerings_csv(db: Session = Depends(get_db)):
    import csv
    from io import StringIO
    
    peerings = db.query(BGPPeering).all()
    
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Role', 'Status', 'State', 'Endpoint A', 'Endpoint Z', 'Created', 'Updated'])
    
    for peering in peerings:
        role_name = peering.role.name if peering.role else ''
        endpoint_a_name = peering.endpoint_a.name if peering.endpoint_a else ''
        endpoint_z_name = peering.endpoint_z.name if peering.endpoint_z else ''
        writer.writerow([
            peering.name,
            role_name,
            peering.status,
            peering.state or '',
            endpoint_a_name,
            endpoint_z_name,
            peering.created_at.isoformat(),
            peering.updated_at.isoformat(),
        ])
    
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bgp-peerings.csv"}
    )


@app.get("/api/bgp-peerings/export/json")
async def export_peerings_json(db: Session = Depends(get_db)):
    import json
    from fastapi.responses import Response
    
    peerings = db.query(BGPPeering).all()
    data = []
    
    for peering in peerings:
        data.append({
            'id': peering.id,
            'name': peering.name,
            'role': peering.role.name if peering.role else None,
            'status': peering.status,
            'state': peering.state,
            'endpoint_a': peering.endpoint_a.name if peering.endpoint_a else None,
            'endpoint_z': peering.endpoint_z.name if peering.endpoint_z else None,
            'created_at': peering.created_at.isoformat(),
            'updated_at': peering.updated_at.isoformat(),
        })
    
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=bgp-peerings.json"}
    )


# Relationship/Topology endpoints
@app.get("/api/bgp-peerings/topology")
async def get_bgp_topology(db: Session = Depends(get_db)):
    """Get BGP peering topology graph data"""
    peerings = db.query(BGPPeering).all()
    
    nodes = []
    edges = []
    node_set = set()
    
    for peering in peerings:
        if peering.endpoint_a:
            a_key = f"device_{peering.endpoint_a.device_id}"
            if a_key not in node_set:
                nodes.append({
                    'id': a_key,
                    'label': peering.endpoint_a.name,
                    'type': 'device',
                    'group': peering.endpoint_a.device_id
                })
                node_set.add(a_key)
        
        if peering.endpoint_z:
            z_key = f"device_{peering.endpoint_z.device_id}"
            if z_key not in node_set:
                nodes.append({
                    'id': z_key,
                    'label': peering.endpoint_z.name,
                    'type': 'device',
                    'group': peering.endpoint_z.device_id
                })
                node_set.add(z_key)
        
        if peering.endpoint_a and peering.endpoint_z:
            edges.append({
                'from': f"device_{peering.endpoint_a.device_id}",
                'to': f"device_{peering.endpoint_z.device_id}",
                'label': peering.name,
                'state': peering.state or 'unknown',
                'status': peering.status,
            })
    
    return {'nodes': nodes, 'edges': edges}


@app.get("/api/peer-endpoints/{endpoint_id}/relationships")
async def get_endpoint_relationships(endpoint_id: int, db: Session = Depends(get_db)):
    """Get all relationships for a peer endpoint"""
    endpoint = db.query(PeerEndpoint).filter(PeerEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Peer Endpoint not found")
    
    # Find all peerings that use this endpoint
    peerings_as_a = db.query(BGPPeering).filter(BGPPeering.endpoint_a_id == endpoint_id).all()
    peerings_as_z = db.query(BGPPeering).filter(BGPPeering.endpoint_z_id == endpoint_id).all()
    
    # Get related endpoints
    related_endpoints = []
    for peering in peerings_as_a:
        if peering.endpoint_z:
            related_endpoints.append({
                'id': peering.endpoint_z.id,
                'name': peering.endpoint_z.name,
                'peering_id': peering.id,
                'peering_name': peering.name,
                'role': 'Z-side'
            })
    
    for peering in peerings_as_z:
        if peering.endpoint_a:
            related_endpoints.append({
                'id': peering.endpoint_a.id,
                'name': peering.endpoint_a.name,
                'peering_id': peering.id,
                'peering_name': peering.name,
                'role': 'A-side'
            })
    
    return {
        'endpoint': {
            'id': endpoint.id,
            'name': endpoint.name,
            'device': endpoint.device.name if endpoint.device else None,
        },
        'peerings': {
            'as_a_side': [{'id': p.id, 'name': p.name} for p in peerings_as_a],
            'as_z_side': [{'id': p.id, 'name': p.name} for p in peerings_as_z],
        },
        'related_endpoints': related_endpoints,
    }
