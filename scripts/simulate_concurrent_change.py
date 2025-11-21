#!/usr/bin/env python3
"""Simulate concurrent changes to BGP sessions in Infrahub"""

import os
import sys
import argparse
try:
    from infrahub_sdk import InfrahubClientSync
except ImportError:
    print("ERROR: infrahub_sdk not installed. Install with: pip install infrahub-sdk")
    sys.exit(1)

def simulate_change(session_name: str, field: str, value, infrahub_url: str = None, token: str = None):
    """Simulate a change to a BGP session"""
    if infrahub_url is None:
        infrahub_url = os.getenv("INFRAHUB_URL", "http://localhost:8000")
    if token is None:
        token = os.getenv("INFRAHUB_TOKEN", "18795e9c-b6db-fbff-cf87-10652e494a9a")
    
    try:
        client = InfrahubClientSync(address=infrahub_url, token=token)
    except Exception as e:
        print(f"ERROR: Failed to connect to Infrahub at {infrahub_url}: {e}")
        sys.exit(1)
    
    try:
        sessions = client.filters(kind="NetworkBGPSession", name__value=session_name)
        
        if not sessions:
            print(f"ERROR: Session {session_name} not found")
            sys.exit(1)
        
        session = sessions[0]
        old_value = getattr(session, field, None)
        setattr(session, field, value)
        session.save()
        
        print(f"Simulated: {session_name}.{field} = {value} (was: {old_value})")
    except Exception as e:
        print(f"ERROR: Failed to simulate change: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True)
    parser.add_argument('--field', required=True)
    parser.add_argument('--value', required=True)
    parser.add_argument('--infrahub-url', default=None, help='Defaults to INFRAHUB_URL env var or http://localhost:8000')
    parser.add_argument('--token', default=None, help='Defaults to INFRAHUB_TOKEN env var')
    
    args = parser.parse_args()
    simulate_change(args.session, args.field, args.value, args.infrahub_url, args.token)

