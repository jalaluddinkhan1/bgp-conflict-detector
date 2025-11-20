import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import BGPPeeringsPage from './pages/BGPPeerings';
import BGPPeeringDetailPage from './pages/BGPPeeringDetail';
import PeerGroupDetailPage from './pages/PeerGroupDetail';
import PeerEndpointDetailPage from './pages/PeerEndpointDetail';
import AutonomousSystemDetailPage from './pages/AutonomousSystemDetail';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="routing/bgp-peerings" element={<BGPPeeringsPage />} />
        <Route path="routing/bgp-peerings/:id" element={<BGPPeeringDetailPage />} />
        <Route path="routing/peer-groups/:id" element={<PeerGroupDetailPage />} />
        <Route path="routing/peer-endpoints/:id" element={<PeerEndpointDetailPage />} />
        <Route path="routing/autonomous-systems/:id" element={<AutonomousSystemDetailPage />} />
      </Route>
    </Routes>
  );
}

export default App;
