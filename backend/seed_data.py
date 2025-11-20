from sqlalchemy.orm import Session
from database import SessionLocal
from models import (
    Device, AutonomousSystem, RoutingInstance, PeerGroup,
    PeerEndpoint, PeeringRole, BGPPeering
)
from datetime import datetime


def seed_data():
    db = SessionLocal()
    
    try:
        # Create Autonomous System
        as_obj = db.query(AutonomousSystem).filter(AutonomousSystem.asn == 65535).first()
        if not as_obj:
            as_obj = AutonomousSystem(
                asn=65535,
                description="Public ASN For Nautobot Airports",
                status="Active"
            )
            db.add(as_obj)
            db.commit()
            db.refresh(as_obj)
        
        # Create Devices
        ber_device = db.query(Device).filter(Device.name == "ber-rtr-01").first()
        if not ber_device:
            ber_device = Device(name="ber-rtr-01", status="Active")
            db.add(ber_device)
            db.commit()
            db.refresh(ber_device)
        
        waw_device = db.query(Device).filter(Device.name == "waw-rtr-01").first()
        if not waw_device:
            waw_device = Device(name="waw-rtr-01", status="Active")
            db.add(waw_device)
            db.commit()
            db.refresh(waw_device)
        
        # Create Routing Instances
        ber_ri = db.query(RoutingInstance).filter(
            RoutingInstance.device_id == ber_device.id
        ).first()
        if not ber_ri:
            ber_ri = RoutingInstance(
                device_id=ber_device.id,
                autonomous_system_id=as_obj.id,
                name=f"{ber_device.name} - AS {as_obj.asn}"
            )
            db.add(ber_ri)
            db.commit()
            db.refresh(ber_ri)
        
        waw_ri = db.query(RoutingInstance).filter(
            RoutingInstance.device_id == waw_device.id
        ).first()
        if not waw_ri:
            waw_ri = RoutingInstance(
                device_id=waw_device.id,
                autonomous_system_id=as_obj.id,
                name=f"{waw_device.name} - AS {as_obj.asn}"
            )
            db.add(waw_ri)
            db.commit()
            db.refresh(waw_ri)
        
        # Create Peering Role
        role = db.query(PeeringRole).filter(PeeringRole.name == "test").first()
        if not role:
            role = PeeringRole(name="test")
            db.add(role)
            db.commit()
            db.refresh(role)
        
        # Create Peer Endpoints
        ber_endpoint = db.query(PeerEndpoint).filter(PeerEndpoint.name == "ber-rtr-01").first()
        if not ber_endpoint:
            ber_endpoint = PeerEndpoint(
                name="ber-rtr-01",
                device_id=ber_device.id,
                routing_instance_id=ber_ri.id,
                source_ip_address="20.20.20.20/32",
                enabled=True,
                autonomous_system_id=as_obj.id
            )
            db.add(ber_endpoint)
            db.commit()
            db.refresh(ber_endpoint)
        
        waw_endpoint = db.query(PeerEndpoint).filter(PeerEndpoint.name == "waw-rtr-01").first()
        if not waw_endpoint:
            waw_endpoint = PeerEndpoint(
                name="waw-rtr-01",
                device_id=waw_device.id,
                routing_instance_id=waw_ri.id,
                source_ip_address="9.9.9.9/32",
                enabled=True,
                autonomous_system_id=as_obj.id
            )
            db.add(waw_endpoint)
            db.commit()
            db.refresh(waw_endpoint)
        
        # Create BGP Peering
        peering = db.query(BGPPeering).filter(BGPPeering.name == "ber-rtr-01 ↔ waw-rtr-01").first()
        if not peering:
            peering = BGPPeering(
                name="ber-rtr-01 ↔ waw-rtr-01",
                role_id=role.id,
                status="Active",
                endpoint_a_id=ber_endpoint.id,
                endpoint_z_id=waw_endpoint.id
            )
            db.add(peering)
            db.commit()
        
        # Create Peer Group
        peer_group = db.query(PeerGroup).filter(PeerGroup.name == "Internal Peer Group").first()
        if not peer_group:
            peer_group = PeerGroup(
                name="Internal Peer Group",
                device_id=ber_device.id,
                routing_instance_id=ber_ri.id,
                enabled=True,
                autonomous_system_id=as_obj.id
            )
            db.add(peer_group)
            db.commit()
        
        print("Seed data created successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
