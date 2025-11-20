import React from 'react';
import { Badge } from '@/components/ui/Badge';

interface SessionStateBadgeProps {
  state?: string;
  uptimeSeconds?: number;
  prefixesReceived?: number;
  prefixesAdvertised?: number;
}

const SessionStateBadge: React.FC<SessionStateBadgeProps> = ({
  state,
  uptimeSeconds,
  prefixesReceived,
  prefixesAdvertised,
}) => {
  if (!state) return null;
  
  const getVariant = (state: string) => {
    switch (state.toLowerCase()) {
      case 'established':
        return 'success';
      case 'idle':
      case 'connect':
      case 'active':
        return 'warning';
      case 'opensent':
      case 'openconfirm':
        return 'info';
      default:
        return 'default';
    }
  };
  
  const formatUptime = (seconds: number) => {
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h`;
    return `${Math.floor(seconds / 86400)}d`;
  };
  
  return (
    <div className="flex items-center space-x-2">
      <Badge variant={getVariant(state)}>
        {state}
      </Badge>
      {uptimeSeconds !== undefined && uptimeSeconds > 0 && (
        <span className="text-xs text-gray-500">Uptime: {formatUptime(uptimeSeconds)}</span>
      )}
      {(prefixesReceived !== undefined || prefixesAdvertised !== undefined) && (
        <span className="text-xs text-gray-500">
          Rx: {prefixesReceived || 0} | Tx: {prefixesAdvertised || 0}
        </span>
      )}
    </div>
  );
};

export default SessionStateBadge;
