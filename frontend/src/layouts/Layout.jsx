import {useState} from 'react';
import {NavLink,Outlet,Link} from 'react-router-dom';
import {LayoutDashboard,Building2,ClipboardList,Upload,ScanSearch,History,Wrench,FileText,Bell,Menu,LogOut,HardHat,MapPin} from 'lucide-react';
import {useAuth} from '../hooks/useAuth.jsx';
import {useAsync} from '../hooks/useAsync.js';
import {api,isMock} from '../services/api.js';
const ALL=['Civil Engineer','Infrastructure Inspector','Maintenance Engineer','Infrastructure Manager','Administrator'];
const NAV=[
['/dashboard','Dashboard',LayoutDashboard,ALL],['/assets','Infrastructure',Building2,['Civil Engineer','Maintenance Engineer','Infrastructure Manager','Administrator']],
['/inspections','Inspections',ClipboardList,ALL],['/upload','Image upload',Upload,['Civil Engineer','Infrastructure Inspector','Administrator']],
['/results','Damage analysis',ScanSearch,['Civil Engineer','Infrastructure Inspector','Administrator']],['/history','Inspection history',History,ALL],['/map','Damage map',MapPin,ALL],
['/maintenance','Maintenance',Wrench,['Civil Engineer','Maintenance Engineer','Infrastructure Manager','Administrator']],['/reports','Reports',FileText,ALL]];
export default function Layout(){
 const {user,logout}=useAuth();const [open,setOpen]=useState(false);
 const {data:notes}=useAsync(api.getNotifications,[]);const unread=(notes||[]).filter(n=>!n.read).length;
 return <div className="flex min-h-screen">
 <aside className={`fixed inset-y-0 z-30 w-60 shrink-0 bg-ink p-3 text-slate-200 transition-transform md:static md:translate-x-0 ${open?'translate-x-0':'-translate-x-full'}`}>
  <div className="mb-5 flex items-center gap-2 px-2 py-2 text-lg font-semibold text-white"><HardHat className="text-survey"/>InfraScan</div>
  <nav className="space-y-1">{NAV.filter(n=>n[3].includes(user.role)).map(([to,label,Icon])=><NavLink key={to} to={to} onClick={()=>setOpen(false)} className={({isActive})=>`flex items-center gap-3 rounded-md px-3 py-2 text-sm ${isActive?'bg-steel text-white':'hover:bg-white/10'}`}><Icon className="h-4 w-4"/>{label}</NavLink>)}</nav>
 </aside>
 {open&&<div className="fixed inset-0 z-20 bg-black/40 md:hidden" onClick={()=>setOpen(false)}/>}
 <div className="min-w-0 flex-1">
  <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2">
   <button className="md:hidden" aria-label="Open menu" onClick={()=>setOpen(true)}><Menu/></button>
   <span className="hidden text-sm text-slate-500 sm:block">AI-Powered Crack &amp; Damage Assessment for Civil Infrastructure</span>
   <div className="ml-auto flex items-center gap-4">
    <Link to="/notifications" aria-label="Notifications" className="relative"><Bell className="h-5 w-5"/>{unread>0&&<span className="absolute -right-2 -top-2 rounded-full bg-red-600 px-1.5 text-[10px] text-white">{unread}</span>}</Link>
    <Link to="/profile" className="text-right text-xs leading-tight hover:underline"><div className="font-medium">{user.name}</div><div className="text-slate-500">{user.role}</div></Link>
    <button onClick={logout} className="btn-ghost" aria-label="Log out"><LogOut className="h-4 w-4"/></button></div>
  </header><div className="hazard"/>
  {isMock&&<div className="bg-survey/20 px-4 py-1 text-xs text-amber-900">Demo mode: sample data and demo sign-in. No backend or AI model is connected; nothing here is real security or real inspection output.</div>}
  <main className="p-4 md:p-6"><Outlet/></main></div></div>;}
