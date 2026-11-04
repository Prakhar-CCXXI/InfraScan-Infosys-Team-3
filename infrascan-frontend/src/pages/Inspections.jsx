import {useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {Plus} from 'lucide-react';
import {useAsync} from '../hooks/useAsync.js';
import {useAuth} from '../hooks/useAuth.jsx';
import {api} from '../services/api.js';
import {Card,Loading,Empty,ErrorBox,PageHead,Modal,Field,Badge,DemoTag} from '../components/ui.jsx';
import {SEV_CLS,STATUS_CLS} from '../utils/helpers.js';
import CrackSvg from '../components/CrackSvg.jsx';
import {SEVERITIES} from '../services/mockData.js';
const STATUSES=['Assigned','In Progress','Pending Review','Completed'];
function NewInspection({assets,users,onDone,onClose}){
 const [f,setF]=useState({assetId:'',date:'',inspector:'',status:'Assigned'});const [err,setErr]=useState({});const [msg,setMsg]=useState('');
 const set=k=>e=>setF({...f,[k]:e.target.value});
 const save=async ev=>{ev.preventDefault();const e={};if(!f.assetId)e.assetId='Select an asset.';if(!f.date)e.date='Choose the inspection date.';if(!f.inspector.trim())e.inspector='Assign an inspector.';
  setErr(e);if(Object.keys(e).length)return;try{await api.createInspection(f);onDone();}catch(x){setMsg(x.message);}};
 return <form onSubmit={save} noValidate className="space-y-3">{msg&&<ErrorBox message={msg}/>}
 <Field label="Infrastructure asset" error={err.assetId}><select className="input" value={f.assetId} onChange={set('assetId')}><option value="">Select…</option>{assets.map(a=><option key={a.id} value={a.id}>{a.id} · {a.name}</option>)}</select></Field>
 <Field label="Inspection date" error={err.date}><input type="date" className="input" value={f.date} onChange={set('date')}/></Field>
 <Field label="Assign inspector" error={err.inspector}><select className="input" value={f.inspector} onChange={set('inspector')}><option value="">Select inspector…</option>{users.filter(u=>u.role==='Infrastructure Inspector').map(u=><option key={u.name}>{u.name}</option>)}</select></Field>
 <Field label="Status"><select className="input" value={f.status} onChange={set('status')}>{STATUSES.map(s=><option key={s}>{s}</option>)}</select></Field>
 <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn">Create inspection</button></div></form>;}
export default function Inspections(){
 const {user}=useAuth();const {data,loading,error,reload}=useAsync(async()=>({i:await api.getInspections(),a:await api.getAssets(),u:await api.getUsers()}),[]);
 const [q,setQ]=useState('');const [st,setSt]=useState('');const [open,setOpen]=useState(false);const [mine,setMine]=useState(false);
 const rows=(data?.i||[]).filter(x=>(!st||x.status===st)&&(x.id+x.assetId+x.inspector).toLowerCase().includes(q.toLowerCase())&&(!mine||user.name.includes(x.inspector)));
 return <><PageHead title="Inspections" sub="Create, assign and track inspections"><DemoTag/><button className="btn" onClick={()=>setOpen(true)}><Plus className="h-4 w-4"/>Create inspection</button></PageHead>
 <Card><div className="mb-3 flex flex-wrap items-center gap-2"><input className="input w-56" placeholder="Search ID, asset, inspector" value={q} onChange={e=>setQ(e.target.value)}/>
 <select className="input w-auto" value={st} onChange={e=>setSt(e.target.value)}><option value="">All statuses</option>{STATUSES.map(s=><option key={s}>{s}</option>)}</select>
 <label className="flex items-center gap-1 text-sm"><input type="checkbox" checked={mine} onChange={e=>setMine(e.target.checked)}/>Assigned to me</label></div>
 {loading?<Loading/>:error?<ErrorBox message={error} onRetry={reload}/>:!rows.length?<Empty text="No inspections match your filters."/>:
 <div className="overflow-x-auto"><table className="w-full"><thead><tr><th>ID</th><th>Asset</th><th>Date</th><th>Inspector</th><th>Status</th><th>Severity</th></tr></thead><tbody>{rows.map(x=><tr key={x.id} className="border-t"><td><Link className="text-steel underline" to={`/inspections/${x.id}`}>{x.id}</Link></td><td>{x.assetId}</td><td>{x.date}</td><td>{x.inspector}</td><td><Badge cls={STATUS_CLS[x.status]}>{x.status}</Badge></td><td><Badge cls={SEV_CLS[x.severity]}>{x.severity}</Badge></td></tr>)}</tbody></table></div>}</Card>
 {open&&<Modal title="Create inspection" onClose={()=>setOpen(false)}><NewInspection assets={data?.a||[]} users={data?.u||[]} onClose={()=>setOpen(false)} onDone={()=>{setOpen(false);reload();}}/></Modal>}</>;}
export function InspectionDetail(){
 const {id}=useParams();
 const {data,loading,error}=useAsync(async()=>{const all=await api.getInspections();const cur=all.find(x=>x.id===id)||null;const prev=cur?all.filter(x=>x.assetId===cur.assetId&&x.date<cur.date&&x.status==='Completed').sort((a,b)=>b.date.localeCompare(a.date))[0]||null:null;return{cur,prev};},[id]);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error}/>;if(!data.cur)return <Empty text="Inspection not found."/>;
 const {cur,prev}=data;const rows=[['Inspection ID',cur.id],['Infrastructure ID',cur.assetId],['Inspection date',cur.date],['Inspector',cur.inspector],['Status',cur.status],['Uploaded images',cur.images],['Detected defects',cur.defects],['Severity',cur.severity],['Maintenance priority',cur.priority]];
 const a=SEVERITIES.indexOf(cur.severity),b=prev?SEVERITIES.indexOf(prev.severity):-1;
 const change=prev&&a>=0&&b>=0?(a>b?'Visible damage level increased':a<b?'Visible damage level decreased':'No change in damage level'):'Not enough data to compare';
 return <><PageHead title={cur.id} sub="Inspection details"><Link to="/inspections" className="btn-ghost">Back</Link><Link to={`/results/${cur.id}`} className="btn">View damage analysis</Link></PageHead>
 <Card><dl className="grid grid-cols-2 gap-2 text-sm">{rows.map(([k,v])=><div key={k} className="contents"><dt className="text-slate-500">{k}</dt><dd>{v}</dd></div>)}</dl></Card>
 <Card title="Comparison with previous inspection" className="mt-4" right={<DemoTag text="Sample images"/>}>{!prev?<Empty text="No earlier completed inspection for this asset."/>:<>
 <div className="grid max-w-xl grid-cols-2 gap-3"><figure><CrackSvg scale={0.8}/><figcaption className="text-center text-xs">Previous · {prev.id} · {prev.date}</figcaption></figure><figure><CrackSvg scale={1.1}/><figcaption className="text-center text-xs">Current · {cur.id} · {cur.date}</figcaption></figure></div>
 <table className="mt-3 w-full"><thead><tr><th></th><th>Previous</th><th>Current</th></tr></thead><tbody>{[['Severity',prev.severity,cur.severity],['Priority',prev.priority,cur.priority],['Detected defects',prev.defects,cur.defects]].map(([k,x,y])=><tr key={k} className="border-t"><td className="text-slate-500">{k}</td><td>{x}</td><td>{y}</td></tr>)}</tbody></table>
 <p className="mt-2 text-sm font-medium">{change}</p><p className="text-xs text-slate-500">Reliable progression measurement needs comparable viewpoints, calibrated scale and image registration from the AI module.</p></>}</Card></>;}
