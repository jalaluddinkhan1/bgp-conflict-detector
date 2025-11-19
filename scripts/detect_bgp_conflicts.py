#!/usr/bin/env python3
"""
BGP Conflict Detection Engine
Detects concurrent changes to BGP sessions and route-maps
"""

import os
import sys
import json
import yaml
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Any
import httpx
from infrahub_sdk import InfrahubClientSync
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

class BGPConflictDetector:
    def __init__(self, infrahub_url: str, infrahub_token: str):
        self.infrahub_url = infrahub_url
        self.infrahub_token = infrahub_token
        
        # GraphQL client for complex queries
        transport = RequestsHTTPTransport(
            url=f"{infrahub_url}/graphql",
            headers={'Authorization': f'Bearer {infrahub_token}'},
            verify=False
        )
        self.graphql_client = Client(transport=transport, fetch_schema_from_transport=False)
        
        # REST client for simple queries
        self.rest_client = InfrahubClientSync(
            address=infrahub_url,
            token=infrahub_token
        )
    
    def extract_bgp_changes_from_git(self, diff_files: str) -> Dict[str, Any]:
        """
        Parse Git diff for BGP-specific changes
        Returns: {
            device_name: {
                sessions: Set[session_names],
                route_maps: Set[route_map_names],
                file_path: str
            }
        }
        """
        changed_objects = {}
        
        for file_path in diff_files.split():
            if not file_path or not os.path.exists(file_path):
                continue
                
            if "bgp/" not in file_path:
                continue
                
            print(f"📄 Analyzing Git change: {file_path}")
            
            # Extract device name
            parts = file_path.split('/')
            if len(parts) < 3:
                continue
            
            device_name = parts[-1].replace('.yaml', '').replace('.yml', '')
            
            # Load BGP config
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            sessions = set()
            route_maps = set()
            
            # Parse BGP peers/sessions
            for peer in config.get('bgp_peers', []):
                session_name = f"{device_name}_{peer['peer_ip']}"
                sessions.add(session_name)
                
                if 'route_map_in' in peer:
                    route_maps.add(peer['route_map_in'])
                if 'route_map_out' in peer:
                    route_maps.add(peer['route_map_out'])
            
            changed_objects[device_name] = {
                'sessions': sessions,
                'route_maps': route_maps,
                'file_path': file_path,
                'raw_config': config
            }
        
        return changed_objects
    
    def get_recent_bgp_changes_graphql(self, since_minutes: int) -> List[Dict[str, Any]]:
        """
        Query Infrahub for recent BGP changes via GraphQL
        More efficient than REST for complex queries
        """
        query = gql("""
            query GetRecentBGPChanges($since: DateTime!) {
                NetworkBGPSession(changed_at__gte: $since) {
                    count
                    edges {
                        node {
                            id
                            name
                            peer_ip
                            peer_asn
                            route_map_in
                            route_map_out
                            hold_time
                            state
                            changed_at
                            created_by {
                                id
                                display_label
                            }
                            instance {
                                node {
                                    device {
                                        node {
                                            name
                                            id
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """)
        
        cutoff = datetime.now() - timedelta(minutes=since_minutes)
        
        try:
            result = self.graphql_client.execute(query, variable_values={
                "since": cutoff.isoformat()
            })
            
            sessions = []
            for edge in result['NetworkBGPSession']['edges']:
                node = edge['node']
                # Flatten nested structure for easier processing
                device_name = node['instance']['node']['device']['node']['name']
                sessions.append({
                    'id': node['id'],
                    'name': node['name'],
                    'device': device_name,
                    'peer_ip': node['peer_ip'],
                    'peer_asn': node['peer_asn'],
                    'route_map_in': node['route_map_in'],
                    'route_map_out': node['route_map_out'],
                    'hold_time': node['hold_time'],
                    'state': node['state'],
                    'changed_at': node['changed_at'],
                    'changed_by': node['created_by']['display_label']
                })
            
            print(f"🔍 Found {len(sessions)} recent BGP changes in Infrahub")
            return sessions
            
        except Exception as e:
            print(f"⚠️ GraphQL query failed: {e}")
            return []
    
    def check_session_flapping(self, session_name: str, window_minutes: int = 5) -> Dict[str, Any]:
        """
        Check if a BGP session is flapping (high state change frequency)
        """
        query = gql("""
            query GetSessionHistory($name: String!, $since: DateTime!) {
                NetworkBGPSession(name__value: $name) {
                    edges {
                        node {
                            id
                            state
                            changed_at
                        }
                    }
                }
                NetworkBGPSessionLog(
                    object_id__value: $name,
                    changed_at__gte: $since
                ) {
                    count
                }
            }
        """)
        
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        
        try:
            result = self.graphql_client.execute(query, variable_values={
                "name": session_name,
                "since": cutoff.isoformat()
            })
            
            # Simulate flapping detection (simplified)
            # In production, query logs/telemetry
            return {
                'is_flapping': False,  # Placeholder for real telemetry
                'state_changes': 0
            }
        except:
            return {'is_flapping': False, 'state_changes': 0}
    
    def detect_conflicts(self, git_changes: Dict, recent_sessions: List[Dict]) -> List[Dict]:
        """
        Core conflict detection logic
        """
        conflicts = []
        
        for recent_session in recent_sessions:
            device = recent_session['device']
            session_name = recent_session['name']
            
            # Skip if device not in Git changes
            if device not in git_changes:
                continue
            
            git_data = git_changes[device]
            
            # 1. Direct session conflict
            if session_name in git_data['sessions']:
                conflicts.append({
                    'severity': 'HIGH',
                    'type': 'direct_session_conflict',
                    'device': device,
                    'session': session_name,
                    'peer_ip': recent_session['peer_ip'],
                    'changed_by': recent_session['changed_by'],
                    'changed_at': recent_session['changed_at'],
                    'description': f"BGP session {session_name} was recently modified by {recent_session['changed_by']} at {recent_session['changed_at']}"
                })
            
            # 2. Route-map collision
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
                    'peer_ip': recent_session['peer_ip'],
                    'route_map_in': recent_session['route_map_in'],
                    'route_map_out': recent_session['route_map_out'],
                    'changed_by': recent_session['changed_by'],
                    'description': f"Route-map collision: {list(changed_route_maps & session_route_maps)[0]} affects {session_name}"
                })
            
            # 3. BGP instance parameter conflict
            # Check if hold_time or keepalive changed
            # ... (expand as needed)
        
        return conflicts
    
    def write_conflict_report(self, conflicts: List[Dict]):
        """Write detailed report for CI artifacts"""
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
        
        with open('conflict-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # GitLab CI artifact format
        with open('conflict-report.env', 'w') as f:
            f.write(f"CONFLICTS_FOUND={str(len(conflicts) > 0).lower()}\n")
            f.write(f"CONFLICT_COUNT={len(conflicts)}\n")
            f.write(f"HIGH_SEVERITY_COUNT={report['summary']['high_severity']}\n")
        
        return report
    
    def post_mr_comment(self, conflicts: List[Dict]):
        """Post detailed comment to GitLab MR"""
        gitlab_token = os.getenv("GITLAB_TOKEN")
        mr_id = os.getenv("CI_MERGE_REQUEST_IID")
        project_id = os.getenv("CI_PROJECT_ID")
        
        if not all([gitlab_token, mr_id, project_id]):
            print("⚠️ GitLab MR context not available, skipping comment")
            return
        
        if not conflicts:
            return
        
        comment = "🚨 **BGP Conflict Detected**\\n\\n"
        comment += "The following BGP resources have been modified recently:\\n\\n"
        
        for c in conflicts:
            emoji = "🔴" if c['severity'] == 'HIGH' else "🟡"
            comment += f"{emoji} **{c['type'].replace('_', ' ').title()}**\\n"
            comment += f"- **Device:** `{c['device']}`\\n"
            comment += f"- **Session:** `{c['session']}`\\n"
            comment += f"- **Peer IP:** `{c['peer_ip']}`\\n"
            comment += f"- **Changed by:** `{c['changed_by']}` at {c['changed_at']}\\n"
            comment += f"- **Description:** {c['description']}\\n\\n"
        
        comment += "**Action Required:** Please coordinate with the other engineer before merging."
        
        try:
            response = httpx.post(
                f"https://gitlab.com/api/v4/projects/{project_id}/merge_requests/{mr_id}/notes",
                headers={"PRIVATE-TOKEN": gitlab_token},
                json={"body": comment}
            )
            response.raise_for_status()
            print(f"💬 Posted conflict warning to MR #{mr_id}")
        except Exception as e:
            print(f"⚠️ Failed to post MR comment: {e}")

def parse_args():
    parser = argparse.ArgumentParser(description='BGP Conflict Detection')
    parser.add_argument('--diff-files', default=os.getenv('GIT_DIFF_FILES', ''), 
                       help='Space-separated list of changed files')
    parser.add_argument('--window-minutes', type=int, default=5,
                       help='Time window for conflict detection')
    parser.add_argument('--infrahub-url', default=os.getenv('INFRAHUB_URL', 'http://localhost:8000'))
    parser.add_argument('--infrahub-token', default=os.getenv('INFRAHUB_TOKEN', '18795e9c-b6db-fbff-cf87-10652e494a9a'))
    return parser.parse_args()

def main():
    print("🚀 BGP Conflict Detection Engine Starting...")
    args = parse_args()
    
    if not args.diff_files:
        print("✅ No files changed in this commit.")
        sys.exit(0)
    
    print(f"📂 Analyzing {len(args.diff_files.split())} changed files...")
    
    detector = BGPConflictDetector(args.infrahub_url, args.infrahub_token)
    
    # 1. Extract BGP changes from Git
    git_changes = detector.extract_bgp_changes_from_git(args.diff_files)
    
    if not git_changes:
        print("✅ No BGP-related changes detected.")
        sys.exit(0)
    
    print(f"🔍 Found BGP changes for devices: {list(git_changes.keys())}")
    
    # 2. Get recent BGP changes from Infrahub
    recent_sessions = detector.get_recent_bgp_changes_graphql(args.window_minutes)
    
    # 3. Detect conflicts
    conflicts = detector.detect_conflicts(git_changes, recent_sessions)
    
    # 4. Write report
    report = detector.write_conflict_report(conflicts)
    
    if conflicts:
        print(f"❌ {len(conflicts)} conflicts detected!")
        for c in conflicts:
            print(json.dumps(c, indent=2))
        
        # Post GitLab comment
        detector.post_mr_comment(conflicts)
        
        # Save report
        with open('conflict-report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        sys.exit(1)
    
    print("✅ No BGP conflicts detected. Safe to merge.")
    sys.exit(0)

if __name__ == "__main__":
    main()

