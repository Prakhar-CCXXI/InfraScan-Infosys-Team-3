import {useState} from 'react';
import {useAuth} from '../hooks/useAuth.jsx';
import {Card,Field,PageHead} from '../components/ui.jsx';
const PERMS={
'Civil Engineer':['Review AI damage analysis and crack measurements','Confirm severity and request engineering review','View reports and condition history'],
'Infrastructure Inspector':['View assigned and pending inspections','Capture or upload inspection images','View detected defects and inspection history'],
'Maintenance Engineer':['View maintenance priorities and assigned tasks','Update maintenance status','Schedule follow-up inspections'],
'Infrastructure Manager':['View infrastructure condition, damage trends and hotspots','Track high-priority findings and maintenance progress','View reports'],
'Administrator':['Manage infrastructure records','View users, model performance, audit logs and platform health (backend modules)','Access all screens']};
export default function Profile(){
 const {user,updateProfile}=useAuth();const [f,setF]=useState({name:user.name||'',department:user.department||''});const [err,setErr]=useState('');const [ok,setOk]=useState(false);
 const save=e=>{e.preventDefault();setOk(false);if(!f.name.trim()){setErr('Full name is required.');return;}setErr('');updateProfile({name:f.name.trim(),department:f.department.trim()});setOk(true);};
 return <><PageHead title="User profile" sub="Your account and role"/>
 <div className="grid gap-4 lg:grid-cols-2"><Card title="Account"><form onSubmit={save} noValidate className="space-y-3">
  <Field label="Full name" error={err}><input className="input" value={f.name} onChange={e=>setF({...f,name:e.target.value})}/></Field>
  <Field label="Email"><input className="input bg-slate-50" value={user.email||''} readOnly/></Field>
  <Field label="Role"><input className="input bg-slate-50" value={user.role} readOnly/></Field>
  <Field label="Department"><input className="input" value={f.department} onChange={e=>setF({...f,department:e.target.value})}/></Field>
  {ok&&<p className="rounded bg-emerald-50 p-2 text-sm text-emerald-800">Profile saved on this device (demo storage).</p>}
  <button className="btn">Save profile</button></form>
  <p className="mt-3 text-xs text-slate-500">Role changes, password management, sessions and audit logging need the backend (Part 3). Not connected yet.</p></Card>
 <Card title={`What a ${user.role} can do`}><ul className="list-disc space-y-1 pl-5 text-sm">{(PERMS[user.role]||[]).map(p=><li key={p}>{p}</li>)}</ul></Card></div></>;}
