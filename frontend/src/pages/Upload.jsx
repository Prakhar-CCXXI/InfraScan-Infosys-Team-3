import {useState,useRef} from 'react';
import {useNavigate} from 'react-router-dom';
import {UploadCloud,Camera,X,Crop} from 'lucide-react';
import ImageEditor from '../components/ImageEditor.jsx';
import {useAsync} from '../hooks/useAsync.js';
import {api,isMock} from '../services/api.js';
import {Card,Field,PageHead,ErrorBox} from '../components/ui.jsx';
const OK=['image/jpeg','image/png','image/webp'],MAX=10*1024*1024;
export default function Upload(){
 const nav=useNavigate();const {data:assets}=useAsync(api.getAssets,[]);const pick=useRef(),cam=useRef();
 const [files,setFiles]=useState([]);const [errs,setErrs]=useState([]);const [f,setF]=useState({assetId:'',date:'',inspector:'',notes:''});const [fe,setFe]=useState({});
 const [ed,setEd]=useState(null);const [stage,setStage]=useState('idle');const [pct,setPct]=useState(0);const [msg,setMsg]=useState('');
 const add=list=>{const bad=[],good=[];[...list].forEach(x=>{if(!OK.includes(x.type))bad.push(`${x.name}: only JPEG, PNG or WebP allowed.`);else if(x.size>MAX)bad.push(`${x.name}: larger than 10 MB.`);else good.push({file:x,url:URL.createObjectURL(x)});});setErrs(bad);setFiles(p=>[...p,...good]);};
 const remove=i=>{URL.revokeObjectURL(files[i].url);setFiles(files.filter((_,k)=>k!==i));};
 const submit=async()=>{const e={};if(!f.assetId)e.assetId='Select an asset.';if(!f.date)e.date='Choose a date.';if(!f.inspector.trim())e.inspector='Enter inspector name.';if(!files.length)e.files='Add at least one image.';
  setFe(e);if(Object.keys(e).length)return;setStage('sending');setMsg('');setPct(0);const t=setInterval(()=>setPct(p=>Math.min(p+15,90)),150);
  try{const fd=new FormData();files.forEach(x=>fd.append('images',x.file));Object.entries(f).forEach(([k,v])=>fd.append(k,v));const r=await api.uploadImages(fd);setPct(100);setStage('done');setMsg(r.message||'Images sent. Analysis requested.');}
  catch(x){setStage('idle');setMsg(x.message);}finally{clearInterval(t);}};
 return <><PageHead title="Image upload" sub="Capture or upload infrastructure images for AI analysis"/>
 <div className="grid gap-4 lg:grid-cols-2"><Card title="Images">
  <div onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();add(e.dataTransfer.files);}} className="flex flex-col items-center gap-2 rounded-lg border-2 border-dashed border-slate-300 p-8 text-center text-sm">
   <UploadCloud className="h-8 w-8 text-steel"/><p>Drag and drop images here</p><p className="text-xs text-slate-500">JPEG, PNG or WebP, up to 10 MB each</p>
   <div className="flex gap-2"><button type="button" className="btn" onClick={()=>pick.current.click()}>Browse files</button><button type="button" className="btn-ghost" onClick={()=>cam.current.click()}><Camera className="h-4 w-4"/>Use camera</button></div>
   <input ref={pick} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={e=>{add(e.target.files);e.target.value='';}}/>
   <input ref={cam} type="file" accept="image/*" capture="environment" hidden onChange={e=>{add(e.target.files);e.target.value='';}}/></div>
  {fe.files&&<p role="alert" className="mt-2 text-xs text-red-600">{fe.files}</p>}{errs.map(x=><p key={x} role="alert" className="mt-1 text-xs text-red-600">{x}</p>)}
  <div className="mt-3 grid grid-cols-3 gap-2">{files.map((x,i)=><div key={x.url} className="relative"><img src={x.url} alt={x.file.name} className="aspect-square w-full rounded object-cover"/><button type="button" aria-label={`Remove ${x.file.name}`} onClick={()=>remove(i)} className="absolute right-1 top-1 rounded-full bg-ink p-1 text-white"><X className="h-3 w-3"/></button><button type="button" aria-label={`Crop or rotate ${x.file.name}`} onClick={()=>setEd(i)} className="absolute bottom-1 right-1 rounded-full bg-ink p-1 text-white"><Crop className="h-3 w-3"/></button></div>)}</div>{ed!==null&&files[ed]&&<ImageEditor item={files[ed]} onClose={()=>setEd(null)} onApply={nf=>{URL.revokeObjectURL(files[ed].url);setFiles(files.map((y,k)=>k===ed?{file:nf,url:URL.createObjectURL(nf)}:y));setEd(null);}}/>}</Card>
 <Card title="Inspection details"><div className="space-y-3">
  <Field label="Infrastructure asset" error={fe.assetId}><select className="input" value={f.assetId} onChange={e=>setF({...f,assetId:e.target.value})}><option value="">Select…</option>{(assets||[]).map(a=><option key={a.id} value={a.id}>{a.id} · {a.name}</option>)}</select></Field>
  <Field label="Inspection date" error={fe.date}><input type="date" className="input" value={f.date} onChange={e=>setF({...f,date:e.target.value})}/></Field>
  <Field label="Inspector" error={fe.inspector}><input className="input" value={f.inspector} onChange={e=>setF({...f,inspector:e.target.value})}/></Field>
  <Field label="Notes (optional)"><textarea className="input" rows={3} value={f.notes} onChange={e=>setF({...f,notes:e.target.value})}/></Field>
  {stage==='sending'&&<div><div className="h-2 rounded bg-slate-200"><div className="h-2 rounded bg-steel" style={{width:pct+'%'}}/></div><p className="mt-1 text-xs text-slate-500">{isMock?'Simulated progress (mock mode, nothing is uploaded)':'Uploading…'}</p></div>}
  {stage==='done'&&<p className="rounded bg-emerald-50 p-2 text-sm text-emerald-800">{msg}</p>}{stage==='idle'&&msg&&<ErrorBox message={msg}/>}
  <div className="flex gap-2"><button className="btn" disabled={stage==='sending'} onClick={submit}>Submit for analysis</button>{stage==='done'&&<button className="btn-ghost" onClick={()=>nav('/results')}>View sample results</button>}</div></div></Card></div></>;}
