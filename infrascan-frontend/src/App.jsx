import {BrowserRouter,Routes,Route,Navigate} from 'react-router-dom';
import {AuthProvider,useAuth} from './hooks/useAuth.jsx';
import Layout from './layouts/Layout.jsx';
import Auth from './pages/Auth.jsx';import Dashboard from './pages/Dashboard.jsx';import Assets,{AssetDetail} from './pages/Assets.jsx';
import Inspections,{InspectionDetail} from './pages/Inspections.jsx';import Upload from './pages/Upload.jsx';import Results from './pages/Results.jsx';
import History from './pages/History.jsx';import Maintenance from './pages/Maintenance.jsx';import Reports from './pages/Reports.jsx';import Notifications from './pages/Notifications.jsx';
import MapView from './pages/MapView.jsx';import Profile from './pages/Profile.jsx';
const Guard=({children})=>useAuth().user?children:<Navigate to="/login" replace/>;
export default function App(){return <AuthProvider><BrowserRouter><Routes>
 <Route path="/login" element={<Auth mode="login"/>}/><Route path="/register" element={<Auth mode="register"/>}/>
 <Route element={<Guard><Layout/></Guard>}>
  <Route index element={<Navigate to="/dashboard" replace/>}/><Route path="/dashboard" element={<Dashboard/>}/>
  <Route path="/assets" element={<Assets/>}/><Route path="/assets/:id" element={<AssetDetail/>}/>
  <Route path="/inspections" element={<Inspections/>}/><Route path="/inspections/:id" element={<InspectionDetail/>}/>
  <Route path="/upload" element={<Upload/>}/><Route path="/results" element={<Results/>}/><Route path="/results/:id" element={<Results/>}/>
  <Route path="/history" element={<History/>}/><Route path="/maintenance" element={<Maintenance/>}/><Route path="/reports" element={<Reports/>}/><Route path="/notifications" element={<Notifications/>}/><Route path="/map" element={<MapView/>}/><Route path="/profile" element={<Profile/>}/></Route>
 <Route path="*" element={<Navigate to="/dashboard" replace/>}/></Routes></BrowserRouter></AuthProvider>;}
