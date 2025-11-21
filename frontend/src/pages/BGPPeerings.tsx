import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient, BGPPeering } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { formatDate } from '@/lib/utils';

const BGPPeeringsPage: React.FC = () => {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [filters, setFilters] = useState({
    role: '',
    status: '',
    state: '',
    device: '',
    tag: '',
  });
  
  const queryClient = useQueryClient();
  
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [searchQuery, setSearchQuery] = useState('');
  
  const { data: peeringsData, isLoading, isError, error } = useQuery({
    queryKey: ['bgp-peerings', filters, searchQuery, page, pageSize],
    queryFn: () => apiClient.getBGPPeerings({
      ...filters,
      search: searchQuery || undefined,
      skip: (page - 1) * pageSize,
      limit: pageSize,
    }),
  });
  
  const peerings = peeringsData?.items || [];
  const total = peeringsData?.total || 0;
  
  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.deleteBGPPeering(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bgp-peerings'] });
      setSelectedIds([]);
    },
    onError: (error: any) => {
      console.error('Failed to delete peering:', error);
      alert(`Failed to delete peering: ${error.message || 'Unknown error'}`);
    },
  });
  
  const bulkDeleteMutation = useMutation({
    mutationFn: (ids: number[]) => apiClient.bulkDeletePeerings(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bgp-peerings'] });
      setSelectedIds([]);
    },
    onError: (error: any) => {
      console.error('Failed to delete peerings:', error);
      alert(`Failed to delete peerings: ${error.message || 'Unknown error'}`);
    },
  });
  
  const bulkUpdateMutation = useMutation({
    mutationFn: ({ ids, updates }: { ids: number[]; updates: any }) => 
      apiClient.bulkUpdatePeerings(ids, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bgp-peerings'] });
      setSelectedIds([]);
    },
    onError: (error: any) => {
      console.error('Failed to update peerings:', error);
      alert(`Failed to update peerings: ${error.message || 'Unknown error'}`);
    },
  });
  
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(peerings.map((p: BGPPeering) => p.id));
    } else {
      setSelectedIds([]);
    }
  };
  
  const handleSelect = (id: number, checked: boolean) => {
    if (checked) {
      setSelectedIds([...selectedIds, id]);
    } else {
      setSelectedIds(selectedIds.filter((selectedId) => selectedId !== id));
    }
  };
  
  const handleDeleteSelected = () => {
    if (selectedIds.length > 0 && window.confirm(`Delete ${selectedIds.length} selected peerings?`)) {
      bulkDeleteMutation.mutate(selectedIds);
    }
  };
  
  const clearFilters = () => {
    setFilters({ role: '', status: '', state: '', device: '', tag: '' });
    setSearchQuery('');
    setPage(1);
  };
  
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <nav className="text-sm text-gray-500 mb-2">
            <Link to="/" className="hover:text-gray-700">Home</Link>
            <span className="mx-2">/</span>
            <span className="text-gray-900">BGP Peerings</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">BGP Peerings</h1>
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Search peerings..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button variant="secondary" size="sm">
            Configure
          </Button>
          {selectedIds.length > 0 && (
            <Button
              variant="warning"
              size="sm"
              onClick={() => {
                const status = window.prompt('Enter new status (Active/Planned/Deprecated):');
                if (status && ['Active', 'Planned', 'Deprecated'].includes(status)) {
                  bulkUpdateMutation.mutate({ ids: selectedIds, updates: { status } });
                }
              }}
            >
              Bulk Update
            </Button>
          )}
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              window.open('/api/bgp-peerings/export/csv', '_blank');
            }}
          >
            Export CSV
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              window.open('/api/bgp-peerings/export/json', '_blank');
            }}
          >
            Export JSON
          </Button>
          <Button variant="primary" size="sm">
            Add
          </Button>
        </div>
      </div>
      
      <div className="flex gap-6">
        <div className="flex-1 bg-white rounded-lg shadow border border-gray-200">
          <div className="p-4 border-b border-gray-200">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-4 py-3 text-left">
                      <input
                        type="checkbox"
                        checked={peerings.length > 0 && selectedIds.length === peerings.length}
                        onChange={(e) => handleSelectAll(e.target.checked)}
                        className="rounded border-gray-300"
                      />
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Peering</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Role</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Endpoint</th>
                    <th className="px-4 py-3 text-left text-sm font-medium text-gray-700">Endpoint</th>
                    <th className="px-4 py-3 text-right text-sm font-medium text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {isLoading ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        Loading...
                      </td>
                    </tr>
                  ) : isError ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-red-500">
                        Error loading peerings: {error instanceof Error ? error.message : 'Unknown error'}
                      </td>
                    </tr>
                  ) : peerings.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                        No peerings found
                      </td>
                    </tr>
                  ) : (
                    peerings.map((peering: any) => (
                      <tr key={peering.id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-3">
                          <input
                            type="checkbox"
                            checked={selectedIds.includes(peering.id)}
                            onChange={(e) => handleSelect(peering.id, e.target.checked)}
                            className="rounded border-gray-300"
                          />
                        </td>
                        <td className="px-4 py-3">
                          <Link
                            to={`/routing/bgp-peerings/${peering.id}`}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                          >
                            {peering.name}
                          </Link>
                        </td>
                        <td className="px-4 py-3">
                          {peering.role ? (
                            <Badge variant="default">{peering.role.name}</Badge>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {peering.endpoint_a ? (
                            <Link
                              to={`/routing/peer-endpoints/${peering.endpoint_a.id}`}
                              className="text-blue-600 hover:text-blue-800"
                            >
                              {peering.endpoint_a.source_ip_address}
                            </Link>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {peering.endpoint_z ? (
                            <Link
                              to={`/routing/peer-endpoints/${peering.endpoint_z.id}`}
                              className="text-blue-600 hover:text-blue-800"
                            >
                              {peering.endpoint_z.source_ip_address}
                            </Link>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center justify-end space-x-1">
                            <button className="p-1 text-orange-600 hover:bg-orange-50 rounded text-sm">
                              Refresh
                            </button>
                            <button className="p-1 text-yellow-600 hover:bg-yellow-50 rounded text-sm">
                              Edit
                            </button>
                            <button
                              onClick={() => deleteMutation.mutate(peering.id)}
                              className="p-1 text-red-600 hover:bg-red-50 rounded text-sm"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          
          {selectedIds.length > 0 && (
            <div className="p-4 border-t border-gray-200">
              <Button
                variant="danger"
                size="sm"
                onClick={handleDeleteSelected}
              >
                Delete Selected
              </Button>
            </div>
          )}
          
          <div className="p-4 border-t border-gray-200 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <select 
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
              <span className="text-sm text-gray-600">per page</span>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                Showing {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, total)} of {total}
              </div>
              <div className="flex items-center space-x-1">
                <button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                <span className="px-2 py-1 text-sm">{page}</span>
                <button
                  onClick={() => setPage(p => p + 1)}
                  disabled={page * pageSize >= total}
                  className="px-2 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
            </div>
          </div>
        </div>
        
        <div className="w-64 bg-gray-50 rounded-lg border border-gray-200 p-4">
          <h3 className="text-sm font-semibold text-gray-900 mb-4">Q Search</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Role</label>
              <select
                value={filters.role}
                onChange={(e) => setFilters({ ...filters, role: e.target.value })}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="">---------</option>
                <option value="test">test</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
              <select
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="">---------</option>
                <option value="Active">Active</option>
                <option value="Planned">Planned</option>
                <option value="Deprecated">Deprecated</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">State</label>
              <select
                value={filters.state || ''}
                onChange={(e) => setFilters({ ...filters, state: e.target.value })}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="">---------</option>
                <option value="idle">Idle</option>
                <option value="connect">Connect</option>
                <option value="active">Active</option>
                <option value="opensent">OpenSent</option>
                <option value="openconfirm">OpenConfirm</option>
                <option value="established">Established</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Device</label>
              <select
                value={filters.device}
                onChange={(e) => setFilters({ ...filters, device: e.target.value })}
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              >
                <option value="">---------</option>
              </select>
            </div>
            <div className="flex space-x-2">
              <Button variant="primary" size="sm" className="flex-1">
                Apply
              </Button>
              <Button variant="secondary" size="sm" onClick={clearFilters} className="flex-1">
                Clear
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BGPPeeringsPage;
