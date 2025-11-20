import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { apiClient } from '@/lib/api';
import { formatRelativeTime } from '@/lib/utils';

const Dashboard: React.FC = () => {
  const { data: stats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: apiClient.getDashboardStats,
  });
  
  const { data: changeLog } = useQuery({
    queryKey: ['change-log'],
    queryFn: apiClient.getChangeLog,
  });
  
  const panels = [
    {
      title: 'Organization',
      items: [
        { label: 'Sites', count: stats?.sites || 3, description: 'Geographic location' },
        { label: 'Tenants', count: stats?.tenants || 0, description: 'Customers or departments' },
      ],
    },
    {
      title: 'DCIM',
      items: [
        { label: 'Racks', count: stats?.racks || 1, description: 'Equipment racks, optionally organized by group' },
        { label: 'VRFs', count: stats?.vrfs || 1, description: 'Virtual routing and forwarding tables' },
      ],
    },
    {
      title: 'Virtualization',
      items: [
        { label: 'Clusters', count: stats?.clusters || 0, description: 'Clusters of physical hosts in which VMs reside' },
        { label: 'Virtual Machines', count: stats?.virtual_machines || 0, description: 'Virtual compute instances running inside clusters' },
      ],
    },
    {
      title: 'Data Sources',
      items: [
        { label: 'Git Repositories', count: stats?.git_repositories || 2, description: 'Collections of data and/or job files' },
      ],
    },
  ];
  
  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <input
            type="text"
            placeholder="Search..."
            className="px-4 py-2 border border-gray-300 rounded-md w-64"
          />
          <select className="px-4 py-2 border border-gray-300 rounded-md">
            <option>All Objects</option>
          </select>
          <button className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700">
            Search
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {panels.map((panel, idx) => (
          <div key={idx} className="bg-white rounded-lg shadow border border-gray-200 p-6">
            <h3 className="text-lg font-semibold mb-4 text-gray-900">{panel.title}</h3>
            <div className="space-y-3">
              {panel.items.map((item, itemIdx) => (
                <div key={itemIdx} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{item.label}</p>
                    <p className="text-xs text-gray-500 mt-1">{item.description}</p>
                  </div>
                  <span className="bg-gray-100 text-gray-700 rounded-full w-8 h-8 flex items-center justify-center text-sm font-medium">
                    {item.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <div className="bg-white rounded-lg shadow border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Change Log</h3>
        <div className="space-y-2">
          {changeLog?.map((change: any, idx: number) => (
            <div key={idx} className="flex items-center space-x-2 text-sm">
              <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-medium">
                {change.action}
              </span>
              <span className="text-gray-700">
                {change.object_type} <strong>{change.object_name}</strong> {change.user} - {formatRelativeTime(change.timestamp)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
