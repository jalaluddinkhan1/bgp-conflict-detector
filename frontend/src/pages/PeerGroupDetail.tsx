import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { Search, Edit, Trash2 } from 'lucide-react';
import { apiClient, PeerGroup } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { formatDate, formatRelativeTime } from '@/lib/utils';

const PeerGroupDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const groupId = parseInt(id || '0');
  
  const { data: group, isLoading } = useQuery({
    queryKey: ['peer-group', groupId],
    queryFn: () => apiClient.getPeerGroup(groupId),
    enabled: !!groupId,
  });
  
  if (isLoading) {
    return <div className="text-center py-8">Loading...</div>;
  }
  
  if (!group) {
    return <div className="text-center py-8">Peer Group not found</div>;
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <nav className="text-sm text-gray-500">
          <Link to="/" className="hover:text-gray-700">BGP Peer Groups</Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{group.name}</span>
        </nav>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Search BGP Peer Groups"
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
        <h1 className="text-3xl font-bold text-gray-900 mb-2">{group.name}</h1>
        <p className="text-sm text-gray-500 mb-4">
          Created {formatDate(group.created_at)} Updated {formatRelativeTime(group.updated_at)}
        </p>
        
        <div className="flex space-x-1 border-b border-gray-200 mb-6">
          <button className="px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600">
            BGP Peer Group
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
            <h2 className="text-lg font-semibold text-gray-900 mb-4">BGP Peer Group</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Name:</span>
                <span className="text-gray-900">{group.name}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Device:</span>
                <Link to={`/devices/${group.device_id}`} className="text-blue-600 hover:text-blue-800">
                  {group.device?.name || group.device_id}
                </Link>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Routing Instance:</span>
                <Link to={`/routing/routing-instances/${group.routing_instance_id}`} className="text-blue-600 hover:text-blue-800">
                  {group.routing_instance?.name || `${group.device?.name} - AS ${group.autonomous_system_id}`}
                </Link>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Peer Group Template</h2>
            <div className="flex items-center justify-between py-2">
              <span className="text-sm font-medium text-gray-700">Template:</span>
              <span className="text-gray-400">-</span>
            </div>
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Custom Fields</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Next-hop-self:</span>
                <span className="text-gray-400">-</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Send-community:</span>
                <span className="text-gray-400">-</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Ttl-security:</span>
                <span className="text-gray-400">-</span>
              </div>
            </div>
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Tags</h2>
            <p className="text-sm text-gray-500">No tags assigned</p>
          </div>
        </div>
        
        <div className="space-y-6">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Attributes</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Source IP Address:</span>
                <span className="text-gray-400">{group.source_ip_address || '-'}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Source Interface:</span>
                <span className="text-gray-400">{group.source_interface || '-'}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Description:</span>
                <span className="text-gray-400">{group.description || '-'}</span>
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Enabled:</span>
                {group.enabled ? (
                  <span className="text-green-600">✓</span>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Autonomous System:</span>
                {group.autonomous_system_id && (
                  <div className="flex items-center space-x-2">
                    <span className="text-blue-600">AS {group.autonomous_system_id}</span>
                    <Badge variant="info">
                      {group.device?.name} - AS {group.autonomous_system_id}
                    </Badge>
                  </div>
                )}
              </div>
              {group.tags && group.tags.length > 0 && (
                <div className="flex items-center justify-between py-2">
                  <span className="text-sm font-medium text-gray-700">Tags:</span>
                  <div className="flex flex-wrap gap-1">
                    {group.tags.map((tag) => (
                      <Badge key={tag.id} variant="default" style={{ backgroundColor: tag.color + '20', color: tag.color }}>
                        {tag.name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Policy</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Import Policy:</span>
                {group.import_policy ? (
                  <Link to={`/routing/routing-policies/${group.import_policy.id}`} className="text-blue-600 hover:text-blue-800">
                    {group.import_policy.name}
                  </Link>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Export Policy:</span>
                {group.export_policy ? (
                  <Link to={`/routing/routing-policies/${group.export_policy.id}`} className="text-blue-600 hover:text-blue-800">
                    {group.export_policy.name}
                  </Link>
                ) : (
                  <span className="text-gray-400">-</span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PeerGroupDetailPage;
