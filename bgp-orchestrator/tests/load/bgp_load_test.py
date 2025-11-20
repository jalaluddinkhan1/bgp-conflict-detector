"""
Locust Load Test for BGP Orchestrator API

Alternative to K6, using Locust for Python-based load testing.

Simulates:
- 100 concurrent users
- Each user creates 10 BGP peerings
- Tests GET /api/v1/bgp-peerings with pagination
- Measures p99 latency

Usage:
    locust -f bgp_load_test.py --host=http://localhost:8000 --users 100 --spawn-rate 10
    locust -f bgp_load_test.py --host=http://localhost:8000 --headless --users 100 --spawn-rate 10 --run-time 5m
"""
import random
import time
from typing import Optional

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser


class BGPPeeringUser(FastHttpUser):
    """Locust user class for BGP Peering API load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts. Used for setup."""
        self.auth_token = self.environment.parsed_options.auth_token if hasattr(self.environment.parsed_options, 'auth_token') else None
        self.peering_ids = []
        self.user_id = random.randint(1, 10000)
        
        # Health check
        response = self.client.get("/healthz", name="health_check")
        if response.status_code != 200:
            print(f"Warning: Health check failed with status {response.status_code}")
    
    def generate_peering_data(self, peering_index: int) -> dict:
        """Generate random BGP peering data."""
        local_asn = 65000 + (self.user_id % 100)
        peer_asn = 65000 + random.randint(1, 1000)
        peer_ip = f"{random.randint(10, 172)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        
        return {
            "name": f"load-test-peering-{self.user_id}-{peering_index}-{random.randint(1000, 9999)}",
            "local_asn": local_asn,
            "peer_asn": peer_asn,
            "peer_ip": peer_ip,
            "hold_time": random.randint(90, 360),
            "keepalive": random.randint(30, 120),
            "device": f"router-{self.user_id % 10}",
            "interface": f"ethernet-0/0/{peering_index}",
            "status": "active",
            "address_families": ["ipv4_unicast"],
            "routing_policy": {
                "import_policy": f"import-policy-{self.user_id}",
                "export_policy": f"export-policy-{self.user_id}",
            },
        }
    
    @task(5)
    def create_peering(self):
        """Create a BGP peering (weight: 5)."""
        peering_data = self.generate_peering_data(len(self.peering_ids))
        
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        with self.client.post(
            "/api/v1/bgp-peerings",
            json=peering_data,
            headers=headers,
            name="create_peering",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                try:
                    body = response.json()
                    if "id" in body:
                        self.peering_ids.append(body["id"])
                        response.success()
                    else:
                        response.failure("Response missing ID")
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(10)
    def list_peerings(self):
        """List BGP peerings with pagination (weight: 10)."""
        page = random.randint(0, 10)
        limit = random.choice([10, 50, 100])
        
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        with self.client.get(
            f"/api/v1/bgp-peerings?skip={page * limit}&limit={limit}",
            headers=headers,
            name="list_peerings",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    body = response.json()
                    if isinstance(body, list):
                        response.success()
                    else:
                        response.failure("Response is not an array")
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(3)
    def get_peering(self):
        """Get a specific peering by ID (weight: 3)."""
        if not self.peering_ids:
            return
        
        peering_id = random.choice(self.peering_ids)
        
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        with self.client.get(
            f"/api/v1/bgp-peerings/{peering_id}",
            headers=headers,
            name="get_peering",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                try:
                    body = response.json()
                    if body.get("id") == peering_id:
                        response.success()
                    else:
                        response.failure("ID mismatch")
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            elif response.status_code == 404:
                # Peering might have been deleted, remove from list
                if peering_id in self.peering_ids:
                    self.peering_ids.remove(peering_id)
                response.failure("Peering not found")
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(2)
    def filter_peerings(self):
        """Filter peerings by device and status (weight: 2)."""
        device = f"router-{self.user_id % 10}"
        status = random.choice(["active", "pending", "disabled"])
        
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        with self.client.get(
            f"/api/v1/bgp-peerings?device={device}&status={status}",
            headers=headers,
            name="filter_peerings",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")


# Custom event handlers for metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts."""
    print(f"Starting load test against {environment.host}")
    print(f"Target: {environment.runner.target_user_count} users")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops."""
    print(f"Load test completed for {environment.host}")
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min response time: {stats.total.min_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per second: {stats.total.total_rps:.2f}")


# Add custom command line options
def add_custom_arguments(parser):
    """Add custom command line arguments."""
    parser.add_argument(
        "--auth-token",
        type=str,
        help="Authentication token for API requests",
    )


# Register custom arguments
events.init_command_line_parser.add_listener(add_custom_arguments)

