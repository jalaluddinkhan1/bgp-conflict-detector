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

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h1>
            <p className="text-gray-700 mb-4">
              {this.state.error?.message || 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: undefined });
                window.location.reload();
              }}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function App() {
  return (
    <ErrorBoundary>
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
    </ErrorBoundary>
  );
}

export default App;
