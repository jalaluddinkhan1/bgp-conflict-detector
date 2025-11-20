import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, Link } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { formatDate, formatRelativeTime } from '@/lib/utils';

const AutonomousSystemDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const asId = parseInt(id || '0');
  
  const { data: as_obj, isLoading } = useQuery({
    queryKey: ['autonomous-system', asId],
    queryFn: () => apiClient.getAutonomousSystem(asId),
    enabled: !!asId,
  });
  
  if (isLoading) {
    return <div className="text-center py-8">Loading...</div>;
  }
  
  if (!as_obj) {
    return <div className="text-center py-8">Autonomous System not found</div>;
  }
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <nav className="text-sm text-gray-500">
          <Link to="/" className="hover:text-gray-700">Autonomous Systems</Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">AS {as_obj.asn}</span>
        </nav>
        <div className="flex items-center space-x-2">
          <div className="flex items-center space-x-2">
            <input
              type="text"
              placeholder="Search Autonomous systems"
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
        <h1 className="text-3xl font-bold text-gray-900 mb-2">AS {as_obj.asn}</h1>
        <p className="text-sm text-gray-500 mb-4">
          Created {formatDate(as_obj.created_at)} • Updated {formatRelativeTime(as_obj.updated_at)}
        </p>
        
        <div className="flex space-x-1 border-b border-gray-200 mb-6">
          <button className="px-4 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600">
            Autonomous System
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
            Advanced
          </button>
          <button className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
            Change Log
          </button>
        </div>
      </div>
      
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">BGP Autonomous System</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between py-2 border-b border-gray-100">
            <span className="text-sm font-medium text-gray-700">ASN:</span>
            <span className="text-gray-900">{as_obj.asn}</span>
          </div>
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm font-medium text-gray-700">Description:</span>
                <span className="text-gray-900">{as_obj.description || '-'}</span>
              </div>
              {as_obj.rir && (
                <div className="flex items-center justify-between py-2 border-b border-gray-100">
                  <span className="text-sm font-medium text-gray-700">RIR:</span>
                  <span className="text-gray-900">{as_obj.rir}</span>
                </div>
              )}
              <div className="flex items-center justify-between py-2">
                <span className="text-sm font-medium text-gray-700">Status:</span>
                <Badge variant="success">{as_obj.status}</Badge>
              </div>
        </div>
      </div>
      
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Tags</h2>
        {as_obj.tags && as_obj.tags.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {as_obj.tags.map((tag) => (
              <Badge key={tag.id} variant="default" style={{ backgroundColor: tag.color + '20', color: tag.color }}>
                {tag.name}
              </Badge>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No tags assigned</p>
        )}
      </div>
    </div>
  );
};

export default AutonomousSystemDetailPage;
