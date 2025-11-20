import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Device {
  id: number;
  name: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AutonomousSystem {
  id: number;
  asn: number;
  description?: string;
  status: string;
  rir?: string;
  created_at: string;
  updated_at: string;
  tags?: Tag[];
}

export interface PeerEndpoint {
  id: number;
  name: string;
  device_id: number;
  routing_instance_id: number;
  peer_group_id?: number;
  source_ip_address: string;
  source_interface?: string;
  description?: string;
  enabled: boolean;
  autonomous_system_id: number;
  import_policy_id?: number;
  export_policy_id?: number;
  import_policy?: RoutingPolicy;
  export_policy?: RoutingPolicy;
  hold_time?: number;
  keepalive?: number;
  remote_endpoint_id?: number;
  created_at: string;
  updated_at: string;
  device?: Device;
  routing_instance?: any;
  autonomous_system?: AutonomousSystem;
}

export interface PeeringRole {
  id: number;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface BGPPeering {
  id: number;
  name: string;
  role_id?: number;
  status: string;
  endpoint_a_id: number;
  endpoint_z_id: number;
  state?: string;
  last_state_change?: string;
  created_at: string;
  updated_at: string;
  role?: PeeringRole;
  endpoint_a?: PeerEndpoint;
  endpoint_z?: PeerEndpoint;
  tags?: Tag[];
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
  color: string;
  description?: string;
  created_at: string;
}

export interface AddressFamily {
  id: number;
  routing_instance_id: number;
  afi: string;
  safi: string;
  enabled: boolean;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface RoutingPolicy {
  id: number;
  name: string;
  description?: string;
  type: string;
  rules?: any;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface Secret {
  id: number;
  name: string;
  type: string;
  secret_value: string;
  description?: string;
  peer_endpoint_id?: number;
  created_at: string;
  updated_at: string;
}

export interface BGPSessionState {
  id: number;
  peering_id: number;
  state: string;
  last_state_change?: string;
  uptime_seconds: number;
  prefixes_received: number;
  prefixes_advertised: number;
  error_message?: string;
  updated_at: string;
}

export interface ChangeLogEntry {
  id: number;
  action: string;
  object_type: string;
  object_id: number;
  object_name: string;
  user: string;
  changes?: any;
  timestamp: string;
}

export interface PeerGroup {
  id: number;
  name: string;
  device_id: number;
  routing_instance_id: number;
  template_id?: number;
  source_ip_address?: string;
  source_interface?: string;
  description?: string;
  enabled: boolean;
  autonomous_system_id?: number;
  import_policy_id?: number;
  export_policy_id?: number;
  import_policy?: RoutingPolicy;
  export_policy?: RoutingPolicy;
  created_at: string;
  updated_at: string;
  device?: Device;
  routing_instance?: any;
  autonomous_system?: AutonomousSystem;
  tags?: Tag[];
}

export const apiClient = {
  // BGP Peerings
  getBGPPeerings: async (params?: { 
    role?: string; 
    status?: string; 
    state?: string;
    device?: string; 
    tag?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }) => {
    const response = await api.get<{ items: BGPPeering[]; total: number; skip: number; limit: number }>('/bgp-peerings', { params });
    return response.data;
  },
  getBGPPeering: async (id: number) => {
    const response = await api.get<BGPPeering>(`/bgp-peerings/${id}`);
    return response.data;
  },
  createBGPPeering: async (data: Partial<BGPPeering>) => {
    const response = await api.post<BGPPeering>('/bgp-peerings', data);
    return response.data;
  },
  deleteBGPPeering: async (id: number) => {
    const response = await api.delete(`/bgp-peerings/${id}`);
    return response.data;
  },
  
  // Autonomous Systems
  getAutonomousSystems: async () => {
    const response = await api.get<AutonomousSystem[]>('/autonomous-systems');
    return response.data;
  },
  getAutonomousSystem: async (id: number) => {
    const response = await api.get<AutonomousSystem>(`/autonomous-systems/${id}`);
    return response.data;
  },
  createAutonomousSystem: async (data: Partial<AutonomousSystem>) => {
    const response = await api.post<AutonomousSystem>('/autonomous-systems', data);
    return response.data;
  },
  
  // Peer Groups
  getPeerGroups: async () => {
    const response = await api.get<PeerGroup[]>('/peer-groups');
    return response.data;
  },
  getPeerGroup: async (id: number) => {
    const response = await api.get<PeerGroup>(`/peer-groups/${id}`);
    return response.data;
  },
  
  // Peer Endpoints
  getPeerEndpoints: async () => {
    const response = await api.get<PeerEndpoint[]>('/peer-endpoints');
    return response.data;
  },
  getPeerEndpoint: async (id: number) => {
    const response = await api.get<PeerEndpoint>(`/peer-endpoints/${id}`);
    return response.data;
  },
  
  // Devices
  getDevices: async () => {
    const response = await api.get<Device[]>('/devices');
    return response.data;
  },
  
  // Dashboard
  getDashboardStats: async () => {
    const response = await api.get('/dashboard/stats');
    return response.data;
  },
  
  // Change Log
  getChangeLog: async (params?: { object_type?: string; user?: string }) => {
    const response = await api.get('/change-log', { params });
    return response.data;
  },
  
  // Address Families
  getAddressFamilies: async (params?: { routing_instance_id?: number }) => {
    const response = await api.get('/address-families', { params });
    return response.data;
  },
  getAddressFamily: async (id: number) => {
    const response = await api.get(`/address-families/${id}`);
    return response.data;
  },
  createAddressFamily: async (data: Partial<AddressFamily>) => {
    const response = await api.post('/address-families', data);
    return response.data;
  },
  
  // Routing Policies
  getRoutingPolicies: async () => {
    const response = await api.get('/routing-policies');
    return response.data;
  },
  getRoutingPolicy: async (id: number) => {
    const response = await api.get(`/routing-policies/${id}`);
    return response.data;
  },
  createRoutingPolicy: async (data: Partial<RoutingPolicy>) => {
    const response = await api.post('/routing-policies', data);
    return response.data;
  },
  
  // Tags
  getTags: async () => {
    const response = await api.get('/tags');
    return response.data;
  },
  getTag: async (id: number) => {
    const response = await api.get(`/tags/${id}`);
    return response.data;
  },
  createTag: async (data: Partial<Tag>) => {
    const response = await api.post('/tags', data);
    return response.data;
  },
  
  // Secrets
  getSecrets: async () => {
    const response = await api.get('/secrets');
    return response.data;
  },
  getSecret: async (id: number) => {
    const response = await api.get(`/secrets/${id}`);
    return response.data;
  },
  
  // BGP Session States
  getSessionStates: async (params?: { peering_id?: number }) => {
    const response = await api.get('/bgp-session-states', { params });
    return response.data;
  },
  getSessionState: async (id: number) => {
    const response = await api.get(`/bgp-session-states/${id}`);
    return response.data;
  },
  updateSessionState: async (id: number, data: Partial<SessionState>) => {
    const response = await api.put(`/bgp-session-states/${id}`, data);
    return response.data;
  },
  
  // Bulk Operations
  bulkDeletePeerings: async (ids: number[]) => {
    const response = await api.post('/bgp-peerings/bulk-delete', ids);
    return response.data;
  },
  bulkUpdatePeerings: async (ids: number[], updates: any) => {
    const response = await api.put('/bgp-peerings/bulk-update', { peering_ids: ids, updates });
    return response.data;
  },
};

export interface AddressFamily {
  id: number;
  routing_instance_id: number;
  afi: string;
  safi: string;
  enabled: boolean;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface RoutingPolicy {
  id: number;
  name: string;
  description?: string;
  type: string;
  rules?: any;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
  color: string;
  description?: string;
  created_at: string;
}

export interface Secret {
  id: number;
  name: string;
  type: string;
  secret_value: string;
  description?: string;
  peer_endpoint_id?: number;
  created_at: string;
  updated_at: string;
}

export interface SessionState {
  id: number;
  peering_id: number;
  state: string;
  last_state_change?: string;
  uptime_seconds: number;
  prefixes_received: number;
  prefixes_advertised: number;
  error_message?: string;
  updated_at: string;
}

export default api;
