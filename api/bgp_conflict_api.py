#!/usr/bin/env python3
"""FastAPI BGP Conflict Detection Service"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import httpx
from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport

app = FastAPI(
    title="BGP Conflict Detection API",
    description="Real-time BGP change conflict detection",
    version="1.0.0"
)

# In-memory cache for performance
change_cache: Dict[str, Dict] = {}

class BGPConflictCheck(BaseModel):
    device_names: List[str] = Field(..., example=["router01", "router02"])
    time_window_minutes: int = Field(default=5, ge=1, le=60)
    check_route_maps: bool = Field(default=True)

class ConflictResponse(BaseModel):
    conflicts_found: bool
    conflict_count: int
    conflicts: List[Dict[str, Any]]
    checked_at: datetime

class InfrahubGraphQLClient:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.transport = HTTPXAsyncTransport(
            url=f"{url}/graphql",
            headers={'Authorization': f'Bearer {token}'}
        )
        self.client = Client(transport=self.transport, fetch_schema_from_transport=False)
    
    async def get_bgp_sessions(self, device_names: List[str]) -> List[Dict]:
        query = gql("""
            query GetBGPSessions($device_names: [String!]!) {
                NetworkBGPInstance(device__name__in: $device_names) {
                    edges {
                        node {
                            id
                            name
                            asn
                            device {
                                node {
                                    name
                                    id
                                }
                            }
                            sessions {
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
                                            display_label
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        """)
        
        async with self.client as session:
            result = await session.execute(query, variable_values={
                "device_names": device_names
            })
            
            sessions = []
            for instance in result['NetworkBGPInstance']['edges']:
                device_name = instance['node']['device']['node']['name']
                for session_edge in instance['node']['sessions']['edges']:
                    node = session_edge['node']
                    sessions.append({
                        'id': node['id'],
                        'name': node['name'],
                        'device': device_name,
                        'peer_ip': node['peer_ip'],
                        'peer_asn': node['peer_asn'],
                        'route_map_in': node['route_map_in'],
                        'route_map_out': node['route_map_out'],
                        'state': node['state'],
                        'changed_at': node['changed_at'],
                        'changed_by': node['created_by']['display_label']
                    })
            
            return sessions

@app.on_event("startup")
async def startup_event():
    """Initialize cache cleanup task"""
    asyncio.create_task(cleanup_cache())

async def cleanup_cache():
    """Remove old cache entries every minute"""
    while True:
        await asyncio.sleep(60)
        now = datetime.now()
        keys_to_delete = [
            k for k, v in change_cache.items()
            if now - v['timestamp'] > timedelta(minutes=10)
        ]
        for k in keys_to_delete:
            del change_cache[k]

@app.post("/bgp/check-conflicts", response_model=ConflictResponse)
async def check_conflicts(request: BGPConflictCheck, background_tasks: BackgroundTasks):
    """
    Check for BGP session conflicts across devices
    """
    client = InfrahubGraphQLClient(
        url=os.getenv("INFRAHUB_URL", "http://localhost:8000"),
        token=os.getenv("INFRAHUB_TOKEN", "18795e9c-b6db-fbff-cf87-10652e494a9a")
    )
    
    sessions = await client.get_bgp_sessions(request.device_names)
    
    cutoff = datetime.now() - timedelta(minutes=request.time_window_minutes)
    recent_sessions = [
        s for s in sessions 
        if datetime.fromisoformat(s['changed_at'].replace('Z', '+00:00')) > cutoff
    ]
    
    # Filter by device
    device_set = set(request.device_names)
    relevant_sessions = [s for s in recent_sessions if s['device'] in device_set]
    
    conflicts = []
    for session in relevant_sessions:
        conflicts.append({
            'type': 'bgp_session_recently_modified',
            'session_id': session['id'],
            'session_name': session['name'],
            'device': session['device'],
            'peer_ip': session['peer_ip'],
            'changed_by': session['changed_by'],
            'changed_at': session['changed_at']
        })
    
    return ConflictResponse(
        conflicts_found=len(conflicts) > 0,
        conflict_count=len(conflicts),
        conflicts=conflicts,
        checked_at=datetime.now()
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(change_cache)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

