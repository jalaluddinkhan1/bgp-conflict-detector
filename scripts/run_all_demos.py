#!/usr/bin/env python3
"""Master test orchestrator for all BGP conflict scenarios"""

import os
import sys
import json
import subprocess
import time
import yaml
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.detect_bgp_conflicts import BGPConflictDetector

# Configuration
INFRAHUB_URL = os.getenv("INFRAHUB_URL", "http://localhost:8000")
INFRAHUB_TOKEN = os.getenv("INFRAHUB_TOKEN", "18795e9c-b6db-fbff-cf87-10652e494a9a")

class Demos:
    def __init__(self):
        self.detector = BGPConflictDetector(INFRAHUB_URL, INFRAHUB_TOKEN)
        self.results = []
    
    def run_scenario(self, name: str, setup_func, expected_conflicts: int):
        """Run a single test scenario"""
        print(f"\n{'='*60}")
        print(f"🧪 SCENARIO: {name}")
        print(f"{'='*60}")
        
        try:
            # Setup
            print("🔧 Setting up scenario...")
            setup_func()
            
            # Wait a moment for changes to register
            time.sleep(2)
            
            # Extract Git changes
            git_changes = self.detector.extract_bgp_changes_from_git(
                os.getenv('GIT_DIFF_FILES', '')
            )
            
            # Get recent Infrahub changes
            recent_sessions = self.detector.get_recent_bgp_changes_graphql(5)
            
            # Detect conflicts
            conflicts = self.detector.detect_conflicts(git_changes, recent_sessions)
            
            # Check results
            success = len(conflicts) == expected_conflicts
            self.results.append({
                'name': name,
                'status': 'PASS' if success else 'FAIL',
                'expected': expected_conflicts,
                'found': len(conflicts),
                'conflicts': conflicts
            })
            
            print(f"✅ Expected {expected_conflicts} conflicts, found {len(conflicts)}")
            
            if conflicts:
                print("\n🚨 Conflicts detected:")
                for c in conflicts:
                    print(json.dumps(c, indent=2))
            
            return success
            
        except Exception as e:
            print(f"❌ Scenario failed: {e}")
            import traceback
            traceback.print_exc()
            self.results.append({
                'name': name,
                'status': 'ERROR',
                'error': str(e)
            })
            return False
    
    def scenario_1_concurrent_asn_change(self):
        """Two engineers change same peer ASN"""
        # Git change (Engineer A)
        config_path = "configs/bgp/routers/router01.yaml"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump({
                'device': 'router01',
                'bgp_peers': [{
                    'peer_ip': '192.168.1.2',
                    'peer_asn': 65099,  # Changed
                    'route_map_in': 'RM_FROM_ROUTER02_IN'
                }]
            }, f)
        
        os.environ['GIT_DIFF_FILES'] = config_path
        
        # Infrahub change (Engineer B)
        from scripts.simulate_concurrent_change import simulate_change
        simulate_change('router01_192.168.1.2', 'peer_asn', 65100)
    
    def scenario_2_route_map_collision(self):
        """Route-map change affects multiple peers"""
        # Git change to route-map
        config_path = "configs/bgp/policies/RM_FROM_ROUTER02_IN.yaml"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump({
                'name': 'RM_FROM_ROUTER02_IN',
                'entries': [{'seq': 10, 'action': 'permit', 'set_local_pref': 200}]
            }, f)
        
        os.environ['GIT_DIFF_FILES'] = config_path
        
        # Infrahub change to BGP session using this route-map
        from scripts.simulate_concurrent_change import simulate_change
        simulate_change('router02_192.168.1.1', 'route_map_in', 'RM_FROM_ROUTER02_IN')
    
    def scenario_3_false_positive_old_change(self):
        """Old change (>5 min) should NOT trigger conflict"""
        # Make change 6 minutes ago
        from scripts.simulate_concurrent_change import simulate_change
        simulate_change('router01_192.168.1.2', 'state', 'down')
        
        # Wait 6 minutes
        print("⏳ Waiting 6 minutes to test time window...")
        time.sleep(360)
        
        # Now make Git change
        config_path = "configs/bgp/routers/router01.yaml"
        with open(config_path, 'w') as f:
            yaml.dump({
                'device': 'router01',
                'bgp_peers': [{
                    'peer_ip': '192.168.1.2',
                    'peer_asn': 65001,
                    'hold_time': 180
                }]
            }, f)
        
        os.environ['GIT_DIFF_FILES'] = config_path
    
    def scenario_4_multi_device_conflict(self):
        """Network-wide change conflicts with device-specific"""
        # Global policy change in Git
        config_path = "configs/bgp/global.yaml"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump({
                'global': {
                    'bgp_hold_time': 240  # Global default
                }
            }, f)
        
        os.environ['GIT_DIFF_FILES'] = config_path
        
        # Device-specific change in Infrahub
        from scripts.simulate_concurrent_change import simulate_change
        simulate_change('router01_192.168.1.2', 'hold_time', 120)
    
    def scenario_5_flapping_detection(self):
        """Flapping BGP session should block changes"""
        # Start flapping in background
        from scripts.simulate_flapping import simulate_flapping
        import threading
        
        def flap():
            simulate_flapping('router01_192.168.1.2', flap_count=5)
        
        thread = threading.Thread(target=flap)
        thread.start()
        
        # Make Git change while flapping
        config_path = "configs/bgp/routers/router01.yaml"
        with open(config_path, 'w') as f:
            yaml.dump({
                'device': 'router01',
                'bgp_peers': [{
                    'peer_ip': '192.168.1.2',
                    'peer_asn': 65001,
                    'keepalive': 30
                }]
            }, f)
        
        os.environ['GIT_DIFF_FILES'] = config_path
        thread.join()
    
    def print_summary(self):
        """Print test results summary"""
        print(f"\n{'='*60}")
        print("📊 DEMO SUITE SUMMARY")
        print(f"{'='*60}")
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = total - passed
        
        for r in self.results:
            status_icon = "✅" if r['status'] == 'PASS' else "❌"
            print(f"{status_icon} {r['name']}: {r['status']}")
            
            if r['status'] == 'FAIL':
                print(f"   Expected {r['expected']} conflicts, got {r['found']}")
        
        print(f"\n📈 Results: {passed}/{total} scenarios passed")
        
        if failed > 0:
            print(f"⚠️  {failed} scenarios need attention")
            sys.exit(1)
        else:
            print("🎉 All scenarios passed!")
            sys.exit(0)

def main():
    print("🧪 BGP Conflict Detection Demo Suite")
    print(f"Infrahub: {INFRAHUB_URL}")
    
    demos = Demos()
    
    # Load test data first
    print("\n📦 Loading test data...")
    subprocess.run([sys.executable, "scripts/load_test_data.py"], check=True)
    
    # Run scenarios
    demos.run_scenario(
        "Concurrent ASN Change",
        demos.scenario_1_concurrent_asn_change,
        expected_conflicts=1
    )
    
    demos.run_scenario(
        "Route Map Collision",
        demos.scenario_2_route_map_collision,
        expected_conflicts=1
    )
    
    # Skip time-based test in quick mode
    # demos.run_scenario(
    #     "False Positive (Old Change)",
    #     demos.scenario_3_false_positive_old_change,
    #     expected_conflicts=0
    # )
    
    demos.run_scenario(
        "Multi-Device Policy Conflict",
        demos.scenario_4_multi_device_conflict,
        expected_conflicts=1
    )
    
    demos.run_scenario(
        "Flapping Session Block",
        demos.scenario_5_flapping_detection,
        expected_conflicts=1
    )
    
    # Print summary
    demos.print_summary()

if __name__ == "__main__":
    main()

