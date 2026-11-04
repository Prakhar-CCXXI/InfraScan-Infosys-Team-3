import {useState} from 'react';
import {Link,useParams} from 'react-router-dom';
import {Plus,Search,Pencil} from 'lucide-react';
import {useAsync} from '../hooks/useAsync.js';
import {api} from '../services/api.js';
import {Card,Loading,Empty,ErrorBox,PageHead,Modal,Field,Badge,DemoTag} from '../components/ui.jsx';
import AssetIcon from '../components/AssetIcon.jsx';
import {TYPES} from '../services/mockData.js';
import {SEV_CLS,STATUS_CLS} from '../utils/helpers.js';
const blank={name:'',type:TYPES[0],location:'',year:'',material:'',department:'',frequency:'6 months',lat:'',lng:''};
function AssetForm({initial,onDone,onClose}){
 const [f,setF]=useState({...blank,...initial});const [err,setErr]=useState({});const [msg,setMsg]=useState('');
 const set=k=>e=>setF({...f,[k]:e.target.value});
 const save=async ev=>{ev.preventDefault();const e={};if(!f.name.trim())e.name='Name is required.';if(!f.location.trim())e.location='Location is required.';
  const y=Number(f.year);if(!y||y<1800||y>new Date().getFullYear())e.year='Enter a year between 1800 and now.';if(!String(f.material).trim())e.material='Material is required.';if(!f.department.trim())e.department='Department is required.';const la=f.lat===''||f.lat==null?null:Number(f.lat),lo=f.lng===''||f.lng==null?null:Number(f.lng);if((la!==null&&!(la>=-90&&la<=90))||(lo!==null&&!(lo>=-180&&lo<=180)))e.lat='Enter valid coordinates.';
  setErr(e);if(Object.keys(e).length)return;try{await api.saveAsset({...f,year:y,lat:la,lng:lo});onDone();}catch(x){setMsg(x.message);}};
 return <form onSubmit={save} noValidate className="space-y-3">{msg&&<ErrorBox message={msg}/>}
 <Field label="Infrastructure name" error={err.name}><input className="input" value={f.name} onChange={set('name')}/></Field>
 <Field label="Infrastructure type"><select className="input" value={f.type} onChange={set('type')}>{TYPES.map(t=><option key={t}>{t}</option>)}</select></Field>
 <Field label="Location" error={err.location}><input className="input" value={f.location} onChange={set('location')}/></Field>
 <div className="grid grid-cols-2 gap-3"><Field label="Construction year" error={err.year}><input className="input" value={f.year} onChange={set('year')}/></Field>
 <Field label="Inspection frequency"><select className="input" value={f.frequency} onChange={set('frequency')}>{['3 months','6 months','12 months'].map(x=><option key={x}>{x}</option>)}</select></Field></div>
 <div className="grid grid-cols-2 gap-3"><Field label="Latitude (for damage map)" error={err.lat}><input className="input" value={f.lat??''} onChange={set('lat')}/></Field><Field label="Longitude"><input className="input" value={f.lng??''} onChange={set('lng')}/></Field></div>
 <Field label="Material type" error={err.material}><input className="input" value={f.material} onChange={set('material')}/></Field>
 <Field label="Responsible department" error={err.department}><input className="input" value={f.department} onChange={set('department')}/></Field>
 <div className="flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button className="btn">Save asset</button></div></form>;}
export default function Assets(){
 const {data,loading,error,reload}=useAsync(api.getAssets,[]);const [q,setQ]=useState('');const [type,setType]=useState('');const [edit,setEdit]=useState(null);
 const rows=(data||[]).filter(a=>(!type||a.type===type)&&(a.name+a.id+a.location).toLowerCase().includes(q.toLowerCase()));
 return <><PageHead title="Infrastructure assets" sub="Register and manage inspected assets"><DemoTag/><button className="btn" onClick={()=>setEdit({})}><Plus className="h-4 w-4"/>Add asset</button></PageHead>
 <Card><div className="mb-3 flex flex-wrap gap-2"><div className="relative"><Search className="absolute left-2 top-2.5 h-4 w-4 text-slate-400"/><input className="input pl-8" placeholder="Search name, ID, location" value={q} onChange={e=>setQ(e.target.value)}/></div>
 <select className="input w-auto" value={type} onChange={e=>setType(e.target.value)}><option value="">All types</option>{TYPES.map(t=><option key={t}>{t}</option>)}</select></div>
 {loading?<Loading/>:error?<ErrorBox message={error} onRetry={reload}/>:!rows.length?<Empty text="No assets match your filters."/>:
 <div className="overflow-x-auto"><table className="w-full"><thead><tr><th>ID</th><th>Name</th><th>Type</th><th>Location</th><th>Built</th><th>Department</th><th></th></tr></thead><tbody>{rows.map(a=><tr key={a.id} className="border-t"><td>{a.id}</td><td><div className="flex items-center gap-2"><AssetIcon type={a.type}/><Link className="text-steel underline" to={`/assets/${a.id}`}>{a.name}</Link></div></td><td>{a.type}</td><td>{a.location}</td><td>{a.year}</td><td>{a.department}</td><td><button aria-label={`Edit ${a.name}`} className="btn-ghost" onClick={()=>setEdit(a)}><Pencil className="h-3 w-3"/></button></td></tr>)}</tbody></table></div>}</Card>
 {edit&&<Modal title={edit.id?`Edit ${edit.id}`:'Add asset'} onClose={()=>setEdit(null)}><AssetForm initial={edit} onClose={()=>setEdit(null)} onDone={()=>{setEdit(null);reload();}}/></Modal>}</>;}
export function AssetDetail(){
 const {id}=useParams();const {data,loading,error}=useAsync(async()=>({a:await api.getAsset(id),i:(await api.getInspections()).filter(x=>x.assetId===id)}),[id]);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error}/>;const {a,i}=data;
 const rows=[['Infrastructure ID',a.id],['Type',a.type],['Location',a.location],['Construction year',a.year],['Material',a.material],['Responsible department',a.department],['Inspection frequency',a.frequency]];
 return <><PageHead title={a.name} sub={a.id}><Link to="/assets" className="btn-ghost">Back</Link></PageHead>
 <div className="grid gap-4 lg:grid-cols-2"><Card title="Details"><dl className="grid grid-cols-2 gap-2 text-sm">{rows.map(([k,v])=><div key={k} className="contents"><dt className="text-slate-500">{k}</dt><dd>{v}</dd></div>)}</dl></Card>
 <Card title="Maintenance history">{a.history?.length?<ul className="list-disc pl-5 text-sm">{a.history.map(h=><li key={h}>{h}</li>)}</ul>:<Empty text="No maintenance recorded."/>}</Card></div>
 <Card title="Inspection history" className="mt-4">{i.length?<table className="w-full"><thead><tr><th>ID</th><th>Date</th><th>Status</th><th>Severity</th></tr></thead><tbody>{i.map(x=><tr key={x.id} className="border-t"><td><Link className="text-steel underline" to={`/inspections/${x.id}`}>{x.id}</Link></td><td>{x.date}</td><td><Badge cls={STATUS_CLS[x.status]}>{x.status}</Badge></td><td><Badge cls={SEV_CLS[x.severity]}>{x.severity}</Badge></td></tr>)}</tbody></table>:<Empty text="No inspections yet."/>}</Card></>;}
