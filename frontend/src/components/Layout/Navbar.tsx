import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Search, User } from 'lucide-react';
import { cn } from '@/lib/utils';

const Navbar: React.FC = () => {
  const location = useLocation();
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);
  
  const navItems = [
    { label: 'Organization', path: '/organization' },
    { label: 'Devices', path: '/devices' },
    { label: 'IPAM', path: '/ipam' },
    {
      label: 'Routing',
      path: '/routing',
      dropdown: [
        { label: 'Autonomous Systems', path: '/routing/autonomous-systems', icon: '+' },
        { label: 'Peering Roles', path: '/routing/peering-roles', icon: '+' },
        { label: 'Peer Group Templates', path: '/routing/peer-group-templates', icon: '+' },
        { label: 'Routing Instances', path: '/routing/routing-instances', icon: '+' },
        { label: 'Peer Groups', path: '/routing/peer-groups', icon: '+' },
        { label: 'Peerings', path: '/routing/bgp-peerings', icon: '+' },
      ],
    },
    { label: 'Virtualization', path: '/virtualization' },
    { label: 'Circuits', path: '/circuits' },
    { label: 'Power', path: '/power' },
    { label: 'Secrets', path: '/secrets' },
    { label: 'Jobs', path: '/jobs' },
    { label: 'Extensibility', path: '/extensibility' },
    { label: 'Plugins', path: '/plugins' },
  ];
  
  return (
    <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <Link to="/" className="flex items-center space-x-2">
              <div className="flex items-center space-x-1 text-orange-500">
                <ChevronRight size={20} />
                <ChevronRight size={20} />
                <ChevronRight size={20} />
              </div>
              <span className="bg-blue-600 text-white px-3 py-1 rounded-full font-semibold">
                nautobot
              </span>
            </Link>
            
            <div className="flex items-center space-x-1">
              {navItems.map((item) => (
                <div
                  key={item.label}
                  className="relative"
                  onMouseEnter={() => item.dropdown && setActiveDropdown(item.label)}
                  onMouseLeave={() => setActiveDropdown(null)}
                >
                  <Link
                    to={item.path}
                    className={cn(
                      'px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      location.pathname.startsWith(item.path)
                        ? 'bg-gray-100 text-gray-900'
                        : 'text-gray-700 hover:bg-gray-50'
                    )}
                  >
                    {item.label}
                  </Link>
                  
                  {item.dropdown && activeDropdown === item.label && (
                    <div className="absolute top-full left-0 mt-1 w-64 bg-white border border-gray-200 rounded-md shadow-lg z-50">
                      <div className="py-1">
                        {item.dropdown.map((dropdownItem, idx) => (
                          <div key={idx} className="border-b border-gray-100 last:border-0">
                            <Link
                              to={dropdownItem.path}
                              className="flex items-center justify-between px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
                            >
                              <span>{dropdownItem.label}</span>
                              {dropdownItem.icon && (
                                <span className="text-green-500 font-bold">{dropdownItem.icon}</span>
                              )}
                            </Link>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2">
              <input
                type="text"
                placeholder="Search"
                className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button className="bg-blue-600 text-white px-3 py-1.5 rounded-md hover:bg-blue-700">
                <Search size={16} />
              </button>
            </div>
            <div className="flex items-center space-x-2 text-gray-700">
              <User size={18} />
              <span className="text-sm">admin</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
