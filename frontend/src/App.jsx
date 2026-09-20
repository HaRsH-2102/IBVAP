import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { WsProvider } from './api/ws';
import Layout from './Layout';
import Dashboard from './components/Dashboard';
import LiveSurveillance from './pages/LiveSurveillance';
import ANPRCenter from './pages/ANPRCenter';
import Alerts from './pages/Alerts';
import EventHistory from './pages/EventHistory';
import EvidenceExplorer from './pages/EvidenceExplorer';
import Analytics from './pages/Analytics';
import Zones from './pages/Zones';
import SystemHealth from './pages/SystemHealth';
import Settings from './pages/Settings';
import Cameras from './pages/Cameras';
import IncidentDetail from './components/IncidentDetail';
import LiveValidation from './pages/LiveValidation';
import DemoOperator from './pages/DemoOperator';

function App() {
  return (
    <WsProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="live" element={<LiveSurveillance />} />
            <Route path="live-validation" element={<LiveValidation />} />
            <Route path="cameras" element={<Cameras />} />
            <Route path="anpr" element={<ANPRCenter />} />
            <Route path="alerts" element={<Alerts />} />
            <Route path="alerts/:id" element={<IncidentDetail />} />
            <Route path="events" element={<EventHistory />} />
            <Route path="evidence" element={<EvidenceExplorer />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="zones" element={<Zones />} />
            <Route path="health" element={<SystemHealth />} />
            <Route path="settings" element={<Settings />} />
            <Route path="demo-operator" element={<DemoOperator />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </WsProvider>
  );
}

export default App;
