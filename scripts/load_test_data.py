#!/usr/bin/env python3
"""
Load comprehensive BGP test data into Infrahub
"""

import os
import sys
import time
import httpx
from infrahub_sdk import InfrahubClientSync

INFRAHUB_URL = os.getenv("INFRAHUB_URL", "http://localhost:8000")
TOKEN = os.getenv("INFRAHUB_TOKEN", "18795e9c-b6db-fbff-cf87-10652e494a9a")

def wait_for_infrahub():
    """Wait for Infrahub to be ready"""
    print("Waiting for Infrahub to be ready...")
    client = httpx.Client()
    for i in range(30):
        try:
            response = client.get(f"{INFRAHUB_URL}/api/info")
            if response.status_code == 200:
                print("Infrahub is ready!")
                return True
        except:
            pass
        time.sleep(2)
    print("ERROR: Infrahub not ready after 60 seconds")
    sys.exit(1)

def load_test_data():
    """Load comprehensive BGP test data"""
    client = InfrahubClientSync(address=INFRAHUB_URL, token=TOKEN)
    
    print("Cleaning old test data...")
    try:
        # Clean up any existing test data
        for device in client.filters(kind="InfraDevice", name__value="router*"):
            if device.name.startswith(("router01", "router02", "router03")):
                device.delete()
    except:
        pass
    
    print("Creating test infrastructure...")
    
    # Create devices
    devices = [
        {
            "name": "router01",
            "status": "active",
            "device_type": "arista",
            "site": "site1",
            "role": "core"
        },
        {
            "name": "router02",
            "status": "active",
            "device_type": "cisco",
            "site": "site1",
            "role": "core"
        },
        {
            "name": "router03",
            "status": "active",
            "device_type": "juniper",
            "site": "site2",
            "role": "edge"
        }
    ]
    
    device_objs = {}
    for dev_data in devices:
        try:
            device = client.create(kind="InfraDevice", data=dev_data)
            device.save()
            device_objs[dev_data['name']] = device
            print(f"Created device: {dev_data['name']}")
        except Exception as e:
            print(f"WARNING: Failed to create {dev_data['name']}: {e}")
    
    # Create BGP instances
    bgp_instances = {}
    for name, device in device_objs.items():
        try:
            instance = client.create(
                kind="NetworkBGPInstance",
                data={
                    "name": f"bgp_{name}",
                    "asn": 65000 if name == "router01" else 65001 if name == "router02" else 65002,
                    "device": device.id
                }
            )
            instance.save()
            bgp_instances[name] = instance
            print(f"Created BGP instance for {name}")
        except Exception as e:
            print(f"WARNING: Failed to create BGP instance for {name}: {e}")
    
    # Create BGP sessions
    sessions = [
        {
            "name": "router01_192.168.1.2",
            "peer_ip": "192.168.1.2",
            "peer_asn": 65001,
            "route_map_in": "RM_FROM_ROUTER02_IN",
            "route_map_out": "RM_TO_ROUTER02_OUT",
            "instance": bgp_instances["router01"].id,
            "state": "established"
        },
        {
            "name": "router01_192.168.2.2",
            "peer_ip": "192.168.2.2",
            "peer_asn": 65002,
            "route_map_in": "RM_FROM_ROUTER03_IN",
            "route_map_out": "RM_TO_ROUTER03_OUT",
            "instance": bgp_instances["router01"].id,
            "state": "established"
        },
        {
            "name": "router02_192.168.1.1",
            "peer_ip": "192.168.1.1",
            "peer_asn": 65000,
            "route_map_in": "RM_FROM_ROUTER01_IN",
            "route_map_out": "RM_TO_ROUTER01_OUT",
            "instance": bgp_instances["router02"].id,
            "state": "established"
        }
    ]
    
    for session_data in sessions:
        try:
            session = client.create(
                kind="NetworkBGPSession",
                data=session_data
            )
            session.save()
            print(f"Created BGP session: {session_data['name']}")
        except Exception as e:
            print(f"WARNING: Failed to create session {session_data['name']}: {e}")
    
    print("Test data loaded successfully!")
    print("\nAvailable test devices:")
    for name in device_objs.keys():
        print(f"   - {name}")
    print("\nReady to run conflict detection tests!")

if __name__ == "__main__":
    wait_for_infrahub()
    load_test_data()

