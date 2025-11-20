import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import SessionStateBadge from '@/components/BGP/SessionStateBadge';
import { formatDate, formatRelativeTime } from '@/lib/utils';

const BGPPeeringDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const peeringId = parseInt(id || '0');
  
  const { data: peering, isLoading } = useQuery({
    queryKey: ['bgp-peering', peeringId],
    queryFn: () => apiClient.getBGPPeering(peeringId),
    enabled: !!peeringId,
  });
  
  const { data: sessionState } = useQuery({
    queryKey: ['bgp-session-state', peeringId],
    queryFn: () => apiClient.getSessionStates({ peering_id: peeringId }).then(states => states[0]),
    enabled: !!peeringId,
  });
  
  if (isLoading) {
    return <div className="text-center py-8">Loading...</div>;
  }
  
  if (!peering) {
    return <div className="text-center py-8">Peering not found</div>;
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <nav className="text-sm text-gray-500">
          <Link to="/" className="hover:text-gray-700">BGP Peerings</Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{peering.name}</span>
        </nav>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Search BGP Peerings"
              className="px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
            <button className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded hover:bg-gray-200">
              Search
            </button>
          </div>
          <Button variant="warning" size="sm">
            Edit
          </Button>
          <Button variant="danger" size="sm">
            Delete
          </Button>
        </div>
      </div>
      
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{peering.name}</h1>
        <p className="text-sm text-gray-500 mb-4">
          Created {formatDate(peering.created_at)} • Updated {formatRelativeTime(peering.updated_at)}
        </p>
        
        <div className="flex space-x-1 border-b border-gray-200 mb-6">
          <button className="px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600">
            BGP Peering
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
            Advanced
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
            Change Log
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">BGP Peering</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm font-medium text-gray-700">Status:</span>
              <Badge variant="success">{peering.status}</Badge>
            </div>
            {(peering.state || sessionState) && (
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Session State:</span>
                <SessionStateBadge
                  state={peering.state || sessionState?.state}
                  uptimeSeconds={sessionState?.uptime_seconds}
                  prefixesReceived={sessionState?.prefixes_received}
                  prefixesAdvertised={sessionState?.prefixes_advertised}
                />
              </div>
            )}
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-sm font-medium text-gray-700">Role:</span>
              {peering.role ? (
                <Badge variant="default">{peering.role.name}</Badge>
              ) : (
                <span className="text-gray-400">-</span>
              )}
            </div>
            {peering.tags && peering.tags.length > 0 && (
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Tags:</span>
                <div className="flex flex-wrap gap-1">
                  {peering.tags.map((tag) => (
                    <Badge key={tag.id} variant="default" style={{ backgroundColor: tag.color + '20', color: tag.color }}>
                      {tag.name}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Peer Endpoint - A Side</h2>
              <div className="flex space-x-1">
                <button className="p-1 text-blue-600 hover:bg-blue-50 rounded text-sm">
                  Info
                </button>
                <button className="p-1 text-orange-600 hover:bg-orange-50 rounded text-sm">
                  Edit
                </button>
                <button className="p-1 text-red-600 hover:bg-red-50 rounded text-sm">
                  Delete
                </button>
              </div>
            </div>
            {peering.endpoint_a && (
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">Device:</span>
                  <Link to={`/devices/${peering.endpoint_a.device_id}`} className="text-blue-600 hover:text-blue-800">
                    {peering.endpoint_a.name}
                  </Link>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">Local IP Address:</span>
                  <Link to={`/routing/peer-endpoints/${peering.endpoint_a.id}`} className="text-blue-600 hover:text-blue-800">
                    {peering.endpoint_a.source_ip_address}
                  </Link>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">Autonomous System:</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-blue-600">
                      AS {peering.endpoint_a.autonomous_system?.asn || peering.endpoint_a.autonomous_system_id}
                    </span>
                    <Badge variant="info">{peering.endpoint_a.name} - AS {peering.endpoint_a.autonomous_system?.asn || peering.endpoint_a.autonomous_system_id}</Badge>
                  </div>
                </div>
                {peering.endpoint_a.hold_time && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-700">Hold Time:</span>
                    <span className="text-gray-900">{peering.endpoint_a.hold_time}s</span>
                  </div>
                )}
                {peering.endpoint_a.keepalive && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-700">Keepalive:</span>
                    <span className="text-gray-900">{peering.endpoint_a.keepalive}s</span>
                  </div>
                )}
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm font-medium text-gray-700">Peer Group:</span>
                  <span className="text-gray-400">{peering.endpoint_a.peer_group_id ? 'Yes' : 'None'}</span>
                </div>
              </div>
            )}
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Peer Endpoint - Z Side</h2>
              <div className="flex space-x-1">
                <button className="p-1 text-blue-600 hover:bg-blue-50 rounded text-sm">
                  Info
                </button>
                <button className="p-1 text-orange-600 hover:bg-orange-50 rounded text-sm">
                  Edit
                </button>
                <button className="p-1 text-red-600 hover:bg-red-50 rounded text-sm">
                  Delete
                </button>
              </div>
            </div>
            {peering.endpoint_z && (
              <div className="space-y-3">
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">Device:</span>
                  <Link to={`/devices/${peering.endpoint_z.device_id}`} className="text-blue-600 hover:text-blue-800">
                    {peering.endpoint_z.name}
                  </Link>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">Local IP Address:</span>
                  <Link to={`/routing/peer-endpoints/${peering.endpoint_z.id}`} className="text-blue-600 hover:text-blue-800">
                    {peering.endpoint_z.source_ip_address}
                  </Link>
                </div>
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">Autonomous System:</span>
                  <div className="flex items-center space-x-2">
                    <span className="text-blue-600">
                      AS {peering.endpoint_z.autonomous_system?.asn || peering.endpoint_z.autonomous_system_id}
                    </span>
                    <Badge variant="info">{peering.endpoint_z.name} - AS {peering.endpoint_z.autonomous_system?.asn || peering.endpoint_z.autonomous_system_id}</Badge>
                  </div>
                </div>
                {peering.endpoint_z.import_policy && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-700">Import Policy:</span>
                    <Link to={`/routing/routing-policies/${peering.endpoint_z.import_policy.id}`} className="text-blue-600 hover:text-blue-800">
                      {peering.endpoint_z.import_policy.name}
                    </Link>
                  </div>
                )}
                {peering.endpoint_z.export_policy && (
                  <div className="flex items-center justify-between py-2 border-b border-gray-100">
                    <span className="text-sm font-medium text-gray-700">Export Policy:</span>
                    <Link to={`/routing/routing-policies/${peering.endpoint_z.export_policy.id}`} className="text-blue-600 hover:text-blue-800">
                      {peering.endpoint_z.export_policy.name}
                    </Link>
                  </div>
                )}
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm font-medium text-gray-700">Peer Group:</span>
                  <span className="text-gray-400">{peering.endpoint_z.peer_group_id ? 'Yes' : 'None'}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BGPPeeringDetailPage;
