#!/usr/bin/env python3
"""
Generate ExaBGP configuration for 80K BGP peers.

This script generates an ExaBGP configuration file with 80,000 BGP peer
configurations for load testing purposes.

Usage:
    python generate_peers.py > exabgp-80k.conf
"""
import sys

# Configuration
TOTAL_PEERS = 80000
PEERS_PER_GROUP = 1000
BASE_ASN = 65000
BASE_IP_NETWORK = "10.0"
START_IP = 1

def generate_peer_config(peer_index: int, local_ip: str, peer_asn: int) -> str:
    """Generate ExaBGP peer configuration."""
    router_id = local_ip
    return f"""    neighbor {local_ip} {{
        local-address 10.0.0.1;
        local-as {BASE_ASN};
        peer-as {peer_asn};
        router-id {router_id};
        hold-time 180;
        keepalive 60;
        family {{
            ipv4 unicast;
        }}
    }}
"""

def generate_exabgp_config(total_peers: int = TOTAL_PEERS) -> str:
    """Generate complete ExaBGP configuration."""
    config = """# ExaBGP Configuration - Auto-generated for 80K BGP Peers
# Generated for load testing

process {
    receive {
        neighbor-changes;
        neighbor-updates;
    }
    send {
        rate-limit;
    }
}

api {
    processes {
        [ 'exabgp-cli' ];
    }
    neighbor-changes;
}

log {
    destination /var/log/exabgp/exabgp.log;
    level INFO;
}

# Peer groups
"""
    
    # Generate peer groups
    group_num = 1
    peer_index = 0
    
    while peer_index < total_peers:
        config += f"\ngroup peers-group-{group_num} {{\n"
        
        for i in range(min(PEERS_PER_GROUP, total_peers - peer_index)):
            # Calculate IP address
            ip_octet_3 = (peer_index // 254) % 256
            ip_octet_4 = (peer_index % 254) + 1
            local_ip = f"{BASE_IP_NETWORK}.{ip_octet_3}.{ip_octet_4}"
            
            # Calculate peer ASN
            peer_asn = BASE_ASN + (peer_index % 1000) + 1
            
            config += generate_peer_config(peer_index, local_ip, peer_asn)
            peer_index += 1
        
        config += "}\n"
        group_num += 1
    
    return config

if __name__ == "__main__":
    total = int(sys.argv[1]) if len(sys.argv) > 1 else TOTAL_PEERS
    print(generate_exabgp_config(total))

