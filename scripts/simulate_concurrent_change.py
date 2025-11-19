#!/usr/bin/env python3
"""Simulate concurrent changes to BGP sessions in Infrahub"""

import sys
import argparse
from infrahub_sdk import InfrahubClientSync

def simulate_change(session_name: str, field: str, value, infrahub_url: str = "http://localhost:8000", token: str = "18795e9c-b6db-fbff-cf87-10652e494a9a"):
    """Simulate a change to a BGP session"""
    client = InfrahubClientSync(address=infrahub_url, token=token)
    
    sessions = client.filters(kind="NetworkBGPSession", name__value=session_name)
    
    if not sessions:
        print(f"❌ Session {session_name} not found")
        sys.exit(1)
    
    session = sessions[0]
    old_value = getattr(session, field, None)
    setattr(session, field, value)
    session.save()
    
    print(f"🔄 Simulated: {session_name}.{field} = {value} (was: {old_value})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True)
    parser.add_argument('--field', required=True)
    parser.add_argument('--value', required=True)
    parser.add_argument('--infrahub-url', default="http://localhost:8000")
    parser.add_argument('--token', default="18795e9c-b6db-fbff-cf87-10652e494a9a")
    
    args = parser.parse_args()
    simulate_change(args.session, args.field, args.value, args.infrahub_url, args.token)

