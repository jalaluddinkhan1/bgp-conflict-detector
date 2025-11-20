import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { Search, Edit, Trash2, Info, Check } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { formatDate, formatRelativeTime } from '@/lib/utils';

const PeerEndpointDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const endpointId = parseInt(id || '0');
  
  const { data: endpoint, isLoading } = useQuery({
    queryKey: ['peer-endpoint', endpointId],
    queryFn: () => apiClient.getPeerEndpoint(endpointId),
    enabled: !!endpointId,
  });
  
  if (isLoading) {
    return <div className="text-center py-8">Loading...</div>;
  }
  
  if (!endpoint) {
    return <div className="text-center py-8">Peer Endpoint not found</div>;
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <nav className="text-sm text-gray-500">
          <Link to="/" className="hover:text-gray-700">Peer Endpoints</Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{endpoint.name}</span>
        </nav>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Search peer endpoints"
              className="px-3 py-1.5 border border-gray-300 rounded text-sm"
            />
            <button className="bg-gray-100 text-gray-700 px-3 py-1.5 rounded hover:bg-gray-200">
              <Search size={16} />
            </button>
          </div>
          <Button variant="warning" size="sm">
            <Edit size={16} className="mr-2" />
            Edit
          </Button>
          <Button variant="danger" size="sm">
            <Trash2 size={16} className="mr-2" />
            Delete
          </Button>
        </div>
      </div>
      
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{endpoint.name}</h1>
        <p className="text-sm text-gray-500 mb-4">
          Created {formatDate(endpoint.created_at)} Updated {formatRelativeTime(endpoint.updated_at)}
        </p>
        
        <div className="flex space-x-1 border-b border-gray-200 mb-6">
          <button className="px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600">
            Peer Endpoint
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
            Advanced
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
            Extra Attributes
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
            Change Log
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-6">
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">BGP Peer Endpoint</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Device:</span>
                <span className="text-gray-900">{endpoint.name}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Routing Instance:</span>
                <Link to={`/routing/routing-instances/${endpoint.routing_instance_id}`} className="text-blue-600 hover:text-blue-800">
                  {endpoint.name} - AS {endpoint.autonomous_system_id}
                </Link>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Peer Group:</span>
                <span className="text-gray-400">{endpoint.peer_group_id ? 'None' : 'None'}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Peering Session:</span>
                <Link to="/routing/bgp-peerings" className="text-blue-600 hover:text-blue-800">
                  {endpoint.name} &lt;-&gt; {endpoint.name}
                </Link>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Authentication</h2>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-medium text-gray-700">Secrets:</span>
              <span className="text-gray-400">None</span>
            </div>
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Attributes</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Source IP Address:</span>
                <Link to={`/routing/peer-endpoints/${endpoint.id}`} className="text-blue-600 hover:text-blue-800">
                  {endpoint.source_ip_address}
                </Link>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Source Interface:</span>
                <span className="text-gray-400">{endpoint.source_interface || '-'}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Description:</span>
                <span className="text-gray-400">{endpoint.description || '-'}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Enabled:</span>
                {endpoint.enabled ? (
                  <span className="text-green-600">
                    <Check size={18} />
                  </span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Autonomous System:</span>
                <div className="flex items-center space-x-2">
                  <span className="text-blue-600">AS {endpoint.autonomous_system_id}</span>
                  <Badge variant="info">
                    {endpoint.name} - AS {endpoint.autonomous_system_id}
                  </Badge>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Remote Peer Information</h2>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-medium text-gray-700">Remote Endpoint:</span>
              <Link to="/routing/peer-endpoints" className="text-blue-600 hover:text-blue-800">
                waw-rtr-01
              </Link>
            </div>
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Policy</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Import Policy:</span>
                <span className="text-gray-400">{endpoint.import_policy || '-'}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Export Policy:</span>
                <span className="text-gray-400">{endpoint.export_policy || '-'}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PeerEndpointDetailPage;
