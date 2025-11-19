#!/usr/bin/env python3
"""Simulate BGP session flapping"""

import time
import argparse
from infrahub_sdk import InfrahubClientSync

def simulate_flapping(session_name: str, flap_count: int = 5, interval: float = 2.0, infrahub_url: str = "http://localhost:8000", token: str = "18795e9c-b6db-fbff-cf87-10652e494a9a"):
    """Simulate BGP session flapping by toggling state"""
    client = InfrahubClientSync(address=infrahub_url, token=token)
    
    print(f"Starting flapping simulation for {session_name} ({flap_count} flaps)")
    
    for i in range(flap_count):
        sessions = client.filters(kind="NetworkBGPSession", name__value=session_name)
        if not sessions:
            print(f"ERROR: Session {session_name} not found")
            return
        
        session = sessions[0]
        new_state = "down" if i % 2 == 0 else "established"
        session.state = new_state
        session.save()
        
        print(f"  Flap {i+1}/{flap_count}: state -> {new_state}")
        time.sleep(interval)
    
    print(f"Flapping simulation complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True)
    parser.add_argument('--flap-count', type=int, default=5)
    parser.add_argument('--interval', type=float, default=2.0)
    parser.add_argument('--infrahub-url', default="http://localhost:8000")
    parser.add_argument('--token', default="18795e9c-b6db-fbff-cf87-10652e494a9a")
    
    args = parser.parse_args()
    simulate_flapping(args.session, args.flap_count, args.interval, args.infrahub_url, args.token)

