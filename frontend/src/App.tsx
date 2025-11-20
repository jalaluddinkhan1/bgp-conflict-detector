import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactKeycloakProvider } from '@react-keycloak/web';
import { keycloak } from './lib/keycloak';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import BGPPeeringsPage from './pages/BGPPeerings';
import BGPPeeringDetailPage from './pages/BGPPeeringDetail';
import PeerGroupDetailPage from './pages/PeerGroupDetail';
import PeerEndpointDetailPage from './pages/PeerEndpointDetail';
import AutonomousSystemDetailPage from './pages/AutonomousSystemDetail';
import CustomerPortal from './pages/CustomerPortal';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={{
        onLoad: 'check-sso',
        silentCheckSsoRedirectUri: window.location.origin + '/silent-check-sso.html',
        pkceMethod: 'S256',
      }}
    >
      <QueryClientProvider client={queryClient}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="routing/bgp-peerings" element={<BGPPeeringsPage />} />
            <Route path="routing/bgp-peerings/:id" element={<BGPPeeringDetailPage />} />
            <Route path="routing/peer-groups/:id" element={<PeerGroupDetailPage />} />
            <Route path="routing/peer-endpoints/:id" element={<PeerEndpointDetailPage />} />
            <Route path="routing/autonomous-systems/:id" element={<AutonomousSystemDetailPage />} />
            <Route path="customer-portal" element={<CustomerPortal />} />
          </Route>
        </Routes>
      </QueryClientProvider>
    </ReactKeycloakProvider>
  );
}

export default App;
