import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth.jsx';
import Layout from './layouts/Layout.jsx';
import Auth from './pages/Auth.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Assets, { AssetDetail } from './pages/Assets.jsx';
import Inspections, { InspectionDetail } from './pages/Inspections.jsx';
import CreateInspection from './pages/CreateInspection.jsx';
import Upload from './pages/Upload.jsx';
import Results from './pages/Results.jsx';
import History from './pages/History.jsx';
import DamageProgression from './pages/DamageProgression.jsx';
import Maintenance from './pages/Maintenance.jsx';
import Reports from './pages/Reports.jsx';
import Analytics from './pages/Analytics.jsx';
import Models from './pages/Models.jsx';
import Users from './pages/Users.jsx';
import AuditLog from './pages/AuditLog.jsx';
import Notifications from './pages/Notifications.jsx';
import MapView from './pages/MapView.jsx';
import Profile from './pages/Profile.jsx';
import Roles from './pages/Roles.jsx';

const Guard = ({ children }) => {
  const { user } = useAuth();
  return user ? children : <Navigate to="/login" replace />;
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/register" element={<Auth mode="register" />} />
          <Route path="/roles" element={<Roles />} />

          {/* Authenticated Application Routes */}
          <Route
            element={
              <Guard>
                <Layout />
              </Guard>
            }
          >
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />

            {/* Assets */}
            <Route path="/assets" element={<Assets />} />
            <Route path="/assets/:id" element={<AssetDetail />} />

            {/* Inspections */}
            <Route path="/inspections" element={<Inspections />} />
            <Route path="/inspections/new" element={<CreateInspection />} />
            <Route path="/inspections/:id" element={<InspectionDetail />} />

            {/* Upload */}
            <Route path="/upload" element={<Upload />} />
            <Route path="/inspections/upload" element={<Upload />} />

            {/* Results / Damage Analysis */}
            <Route path="/results" element={<Results />} />
            <Route path="/results/:id" element={<Results />} />
            <Route path="/inspections/results" element={<Results />} />

            {/* History & Damage Progression */}
            <Route path="/history" element={<History />} />
            <Route path="/inspections/history" element={<History />} />
            <Route path="/inspections/progression" element={<DamageProgression />} />
            <Route path="/progression" element={<DamageProgression />} />

            {/* Map & Maintenance */}
            <Route path="/map" element={<MapView />} />
            <Route path="/maintenance" element={<Maintenance />} />

            {/* Reports & Analytics */}
            <Route path="/reports" element={<Reports />} />
            <Route path="/analytics" element={<Analytics />} />

            {/* Models & AI Registry */}
            <Route path="/models" element={<Models />} />

            {/* Administration & Operations */}
            <Route path="/users" element={<Users />} />
            <Route path="/audit" element={<AuditLog />} />

            {/* Profile & Notifications */}
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/profile" element={<Profile />} />
          </Route>

          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
