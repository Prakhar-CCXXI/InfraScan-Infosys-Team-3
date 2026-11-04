import {useState} from 'react';
import {Link,useNavigate,Navigate} from 'react-router-dom';
import {Eye,EyeOff,HardHat} from 'lucide-react';
import {useAuth} from '../hooks/useAuth.jsx';
import {Field} from '../components/ui.jsx';
import {ROLES} from '../services/mockData.js';
import Hero from '../components/Hero.jsx';
export default function Auth({mode}){
 const reg=mode==='register';const {user,login,register}=useAuth();const nav=useNavigate();
 const [f,setF]=useState({name:'',email:'',password:'',confirm:'',role:ROLES[1],department:''});
 const [show,setShow]=useState(false);const [err,setErr]=useState({});const [msg,setMsg]=useState('');const [busy,setBusy]=useState(false);
 if(user)return <Navigate to="/dashboard" replace/>;
 const set=k=>e=>setF({...f,[k]:e.target.value});
 const validate=()=>{const e={};if(reg&&!f.name.trim())e.name='Full name is required.';
  if(!f.email)e.email='Email is required.';else if(!/^\S+@\S+\.\S+$/.test(f.email))e.email='Enter a valid email address.';
  if(!f.password)e.password='Password is required.';else if(f.password.length<6)e.password='Use at least 6 characters.';
  if(reg&&f.confirm!==f.password)e.confirm='Passwords do not match.';return e;};
 const submit=async ev=>{ev.preventDefault();setMsg('');const e=validate();setErr(e);if(Object.keys(e).length)return;setBusy(true);
  try{await (reg?register(f):login(f));nav('/dashboard');}catch(x){setMsg(x.message);}finally{setBusy(false);}};
 return <div className="flex min-h-screen bg-ink"><Hero/><div className="flex flex-1 items-center justify-center p-4"><form onSubmit={submit} noValidate className="w-full max-w-md space-y-3 rounded-lg bg-white p-6">
  <div className="flex items-center gap-2 text-lg font-semibold"><HardHat className="text-steel"/>InfraScan</div>
  <p className="text-sm text-slate-500">{reg?'Create your account':'Sign in to manage inspections'}</p>
  {!reg&&<p className="rounded bg-survey/20 p-2 text-xs text-amber-900">Demo sign-in only (not secure authentication): demo@infrascan.test / demo123</p>}
  {msg&&<p role="alert" className="rounded bg-red-50 p-2 text-sm text-red-700">{msg}</p>}
  {reg&&<Field label="Full name" error={err.name}><input className="input" value={f.name} onChange={set('name')}/></Field>}
  <Field label="Email" error={err.email}><input className="input" type="email" value={f.email} onChange={set('email')}/></Field>
  <Field label="Password" error={err.password}><div className="relative"><input className="input pr-10" type={show?'text':'password'} value={f.password} onChange={set('password')}/><button type="button" onClick={()=>setShow(!show)} aria-label="Toggle password visibility" className="absolute right-2 top-2 text-slate-500">{show?<EyeOff className="h-4 w-4"/>:<Eye className="h-4 w-4"/>}</button></div></Field>
  {reg&&<Field label="Confirm password" error={err.confirm}><input className="input" type={show?'text':'password'} value={f.confirm} onChange={set('confirm')}/></Field>}
  <Field label="Role"><select className="input" value={f.role} onChange={set('role')}>{ROLES.map(r=><option key={r}>{r}</option>)}</select></Field>
  {reg&&<Field label="Department (optional)"><input className="input" value={f.department} onChange={set('department')}/></Field>}
  <button className="btn w-full justify-center" disabled={busy}>{busy?'Please wait…':reg?'Create account':'Sign in'}</button>
  <p className="text-center text-sm">{reg?<>Have an account? <Link className="text-steel underline" to="/login">Sign in</Link></>:<>New here? <Link className="text-steel underline" to="/register">Register</Link></>}</p></form></div></div>;}
