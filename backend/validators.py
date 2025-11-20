from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional

def validate_asn(asn: int) -> bool:
    """Validate ASN is in valid range (1-4294967295)"""
    return 1 <= asn <= 4294967295


def validate_ip_address(ip_address: str) -> bool:
    """Basic IP address validation"""
    import ipaddress
    try:
        # Try parsing as IPv4 or IPv6
        ipaddress.ip_interface(ip_address)
        return True
    except ValueError:
        return False


def validate_peering_name(name: str, db: Session, exclude_id: Optional[int] = None) -> bool:
    """Validate peering name is unique"""
    from models import BGPPeering
    query = db.query(BGPPeering).filter(BGPPeering.name == name)
    if exclude_id:
        query = query.filter(BGPPeering.id != exclude_id)
    existing = query.first()
    return existing is None


def validate_endpoint_relationship(endpoint_a_id: int, endpoint_z_id: int, db: Session) -> tuple[bool, str]:
    """Validate that endpoint A and Z are different and valid"""
    from models import PeerEndpoint
    
    if endpoint_a_id == endpoint_z_id:
        return False, "Endpoint A and Z cannot be the same"
    
    endpoint_a = db.query(PeerEndpoint).filter(PeerEndpoint.id == endpoint_a_id).first()
    endpoint_z = db.query(PeerEndpoint).filter(PeerEndpoint.id == endpoint_z_id).first()
    
    if not endpoint_a:
        return False, "Endpoint A not found"
    if not endpoint_z:
        return False, "Endpoint Z not found"
    
    return True, ""


def validate_bgp_state(state: str) -> bool:
    """Validate BGP state is valid"""
    valid_states = ["idle", "connect", "active", "opensent", "openconfirm", "established"]
    return state.lower() in valid_states


def validate_afi_safi(afi: str, safi: str) -> tuple[bool, str]:
    """Validate AFI-SAFI combination"""
    valid_afis = ["ipv4", "ipv6", "vpnv4", "vpnv6", "l2vpn"]
    valid_safis = ["unicast", "multicast", "evpn", "vpls"]
    
    if afi.lower() not in valid_afis:
        return False, f"Invalid AFI: {afi}. Must be one of {valid_afis}"
    
    if safi.lower() not in valid_safis:
        return False, f"Invalid SAFI: {safi}. Must be one of {valid_safis}"
    
    # Validate combinations
    if afi.lower() == "l2vpn" and safi.lower() not in ["evpn", "vpls"]:
        return False, "L2VPN AFI only supports EVPN or VPLS SAFI"
    
    return True, ""


def validate_hold_time(hold_time: int) -> bool:
    """Validate BGP hold time (0 or 3-65535)"""
    return hold_time == 0 or (3 <= hold_time <= 65535)


def validate_keepalive(keepalive: int, hold_time: int) -> tuple[bool, str]:
    """Validate BGP keepalive timer"""
    if keepalive < 0:
        return False, "Keepalive must be non-negative"
    
    if hold_time > 0 and keepalive >= hold_time:
        return False, "Keepalive must be less than hold time"
    
    return True, ""
