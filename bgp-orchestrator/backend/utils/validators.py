"""
BGP data validation utilities.
"""
import ipaddress
from typing import Any


def validate_asn(asn: Any) -> int:
    """
    Validate and return ASN (Autonomous System Number).
    
    Args:
        asn: ASN value (can be int or string)
        
    Returns:
        Validated ASN as integer
        
    Raises:
        ValueError: If ASN is invalid
    """
    try:
        asn_int = int(asn)
        if not (1 <= asn_int <= 4294967295):
            raise ValueError(f"ASN must be between 1 and 4294967295, got {asn_int}")
        return asn_int
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid ASN: {asn}") from e


def validate_ipv4_address(address: str) -> str:
    """
    Validate IPv4 address.
    
    Args:
        address: IPv4 address string
        
    Returns:
        Validated IPv4 address
        
    Raises:
        ValueError: If address is invalid
    """
    try:
        ip = ipaddress.IPv4Address(address)
        return str(ip)
    except (ValueError, ipaddress.AddressValueError) as e:
        raise ValueError(f"Invalid IPv4 address: {address}") from e


def validate_ipv6_address(address: str) -> str:
    """
    Validate IPv6 address.
    
    Args:
        address: IPv6 address string
        
    Returns:
        Validated IPv6 address
        
    Raises:
        ValueError: If address is invalid
    """
    try:
        ip = ipaddress.IPv6Address(address)
        return str(ip)
    except (ValueError, ipaddress.AddressValueError) as e:
        raise ValueError(f"Invalid IPv6 address: {address}") from e


def validate_ipv4_prefix(prefix: str) -> str:
    """
    Validate IPv4 prefix (CIDR notation).
    
    Args:
        prefix: IPv4 prefix in CIDR notation (e.g., "192.0.2.0/24")
        
    Returns:
        Validated IPv4 prefix
        
    Raises:
        ValueError: If prefix is invalid
    """
    try:
        network = ipaddress.IPv4Network(prefix, strict=False)
        return str(network)
    except (ValueError, ipaddress.NetmaskValueError) as e:
        raise ValueError(f"Invalid IPv4 prefix: {prefix}") from e


def validate_ipv6_prefix(prefix: str) -> str:
    """
    Validate IPv6 prefix (CIDR notation).
    
    Args:
        prefix: IPv6 prefix in CIDR notation (e.g., "2001:db8::/32")
        
    Returns:
        Validated IPv6 prefix
        
    Raises:
        ValueError: If prefix is invalid
    """
    try:
        network = ipaddress.IPv6Network(prefix, strict=False)
        return str(network)
    except (ValueError, ipaddress.NetmaskValueError) as e:
        raise ValueError(f"Invalid IPv6 prefix: {prefix}") from e

