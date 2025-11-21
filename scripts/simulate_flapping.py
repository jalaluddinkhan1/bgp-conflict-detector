#!/usr/bin/env python3
"""Simulate BGP session flapping"""

import os
import sys
import time
import argparse
try:
    from infrahub_sdk import InfrahubClientSync
except ImportError:
    print("ERROR: infrahub_sdk not installed. Install with: pip install infrahub-sdk")
    sys.exit(1)

def simulate_flapping(session_name: str, flap_count: int = 5, interval: float = 2.0, infrahub_url: str = None, token: str = None):
    """Simulate BGP session flapping by toggling state"""
    if infrahub_url is None:
        infrahub_url = os.getenv("INFRAHUB_URL", "http://localhost:8000")
    if token is None:
        token = os.getenv("INFRAHUB_TOKEN", "18795e9c-b6db-fbff-cf87-10652e494a9a")
    
    try:
        client = InfrahubClientSync(address=infrahub_url, token=token)
    except Exception as e:
        print(f"ERROR: Failed to connect to Infrahub at {infrahub_url}: {e}")
        sys.exit(1)
    
    print(f"Starting flapping simulation for {session_name} ({flap_count} flaps)")
    
    try:
        for i in range(flap_count):
            try:
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
            except Exception as e:
                print(f"ERROR: Failed to flap session (iteration {i+1}): {e}")
                return
        
        print(f"Flapping simulation complete")
    except KeyboardInterrupt:
        print("\nFlapping simulation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during flapping simulation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True)
    parser.add_argument('--flap-count', type=int, default=5)
    parser.add_argument('--interval', type=float, default=2.0)
    parser.add_argument('--infrahub-url', default=None, help='Defaults to INFRAHUB_URL env var or http://localhost:8000')
    parser.add_argument('--token', default=None, help='Defaults to INFRAHUB_TOKEN env var')
    
    args = parser.parse_args()
    simulate_flapping(args.session, args.flap_count, args.interval, args.infrahub_url, args.token)

