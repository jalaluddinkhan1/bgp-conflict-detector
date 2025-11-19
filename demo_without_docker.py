#!/usr/bin/env python3
"""
Demo script that shows how the BGP Conflict Detection System works
This runs without Docker/Infrahub to demonstrate the logic
"""

import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, List

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def demo_conflict_detection():
    """Demonstrate conflict detection logic"""
    
    print_header("BGP Conflict Detection System Demo")
    print("\n📋 This demo shows how the system detects conflicts")
    print("   without requiring Docker/Infrahub to be running.\n")
    
    # Simulate Git changes
    print_header("Step 1: Analyzing Git Changes")
    git_changes = {
        "router01": {
            "sessions": {"router01_192.168.1.2"},
            "route_maps": {"RM_FROM_ROUTER02_IN"},
            "file_path": "configs/bgp/routers/router01.yaml"
        }
    }
    
    print("📄 Git changes detected:")
    for device, changes in git_changes.items():
        print(f"   Device: {device}")
        print(f"   - Modified sessions: {list(changes['sessions'])}")
        print(f"   - Modified route-maps: {list(changes['route_maps'])}")
        print(f"   - File: {changes['file_path']}")
    
    # Simulate recent Infrahub changes
    print_header("Step 2: Querying Infrahub for Recent Changes")
    recent_sessions = [
        {
            "id": "session-123",
            "name": "router01_192.168.1.2",
            "device": "router01",
            "peer_ip": "192.168.1.2",
            "peer_asn": 65001,
            "route_map_in": "RM_FROM_ROUTER02_IN",
            "route_map_out": "RM_TO_ROUTER02_OUT",
            "changed_at": (datetime.now() - timedelta(minutes=2)).isoformat(),
            "changed_by": "engineer-b@company.com"
        }
    ]
    
    print(f"🔍 Found {len(recent_sessions)} recent BGP changes in Infrahub:")
    for session in recent_sessions:
        print(f"   Session: {session['name']}")
        print(f"   - Device: {session['device']}")
        print(f"   - Peer IP: {session['peer_ip']}")
        print(f"   - Changed by: {session['changed_by']}")
        print(f"   - Changed at: {session['changed_at']}")
    
    # Detect conflicts
    print_header("Step 3: Detecting Conflicts")
    conflicts = []
    
    for recent_session in recent_sessions:
        device = recent_session['device']
        session_name = recent_session['name']
        
        if device in git_changes:
            git_data = git_changes[device]
            
            # Direct session conflict
            if session_name in git_data['sessions']:
                conflicts.append({
                    'severity': 'HIGH',
                    'type': 'direct_session_conflict',
                    'device': device,
                    'session': session_name,
                    'peer_ip': recent_session['peer_ip'],
                    'changed_by': recent_session['changed_by'],
                    'changed_at': recent_session['changed_at'],
                    'description': f"BGP session {session_name} was recently modified by {recent_session['changed_by']}"
                })
            
            # Route-map collision
            changed_route_maps = git_data.get('route_maps', set())
            session_route_maps = {
                recent_session['route_map_in'],
                recent_session['route_map_out']
            } - {None}
            
            if changed_route_maps & session_route_maps:
                conflicts.append({
                    'severity': 'MEDIUM',
                    'type': 'route_map_collision',
                    'device': device,
                    'session': session_name,
                    'route_map_in': recent_session['route_map_in'],
                    'changed_by': recent_session['changed_by'],
                    'description': f"Route-map collision: {list(changed_route_maps & session_route_maps)[0]} affects {session_name}"
                })
    
    # Display results
    print_header("Step 4: Conflict Detection Results")
    
    if conflicts:
        print(f"❌ {len(conflicts)} CONFLICT(S) DETECTED!\n")
        for i, conflict in enumerate(conflicts, 1):
            emoji = "🔴" if conflict['severity'] == 'HIGH' else "🟡"
            print(f"{emoji} Conflict #{i}: {conflict['type'].replace('_', ' ').title()}")
            print(f"   Severity: {conflict['severity']}")
            print(f"   Device: {conflict['device']}")
            print(f"   Session: {conflict['session']}")
            print(f"   Changed by: {conflict['changed_by']}")
            print(f"   Description: {conflict['description']}")
            print()
        
        print("⚠️  ACTION REQUIRED:")
        print("   - Coordinate with the other engineer before merging")
        print("   - Review both changes to avoid conflicts")
        print("   - Consider merging changes together")
    else:
        print("✅ No conflicts detected. Safe to merge!")
    
    # Show report structure
    print_header("Step 5: Generated Report")
    report = {
        'timestamp': datetime.now().isoformat(),
        'conflicts_found': len(conflicts) > 0,
        'conflict_count': len(conflicts),
        'conflicts': conflicts,
        'summary': {
            'high_severity': sum(1 for c in conflicts if c['severity'] == 'HIGH'),
            'medium_severity': sum(1 for c in conflicts if c['severity'] == 'MEDIUM')
        }
    }
    
    print("📊 Conflict Report (JSON format):")
    print(json.dumps(report, indent=2))
    
    # Show what would happen in GitLab CI
    print_header("Step 6: GitLab CI Integration")
    print("In a real GitLab CI pipeline, the system would:")
    print("   1. ✅ Analyze changed files in the merge request")
    print("   2. ✅ Query Infrahub for recent changes (last 5 minutes)")
    print("   3. ✅ Detect conflicts between Git changes and Infrahub changes")
    print("   4. ✅ Post a comment to the MR if conflicts are found")
    print("   5. ✅ Fail the pipeline if HIGH severity conflicts exist")
    print("   6. ✅ Generate artifacts: conflict-report.json")
    
    print_header("Demo Complete!")
    print("\n💡 To run the full system:")
    print("   1. Install Docker Desktop: https://www.docker.com/products/docker-desktop")
    print("   2. Start infrastructure: docker-compose up -d")
    print("   3. Load test data: python scripts/load_test_data.py")
    print("   4. Run full demos: python scripts/run_all_demos.py")
    print("\n📖 See README.md for complete setup instructions")

if __name__ == "__main__":
    demo_conflict_detection()

