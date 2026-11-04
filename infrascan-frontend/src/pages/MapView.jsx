import {useEffect,useRef,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {useAsync} from '../hooks/useAsync.js';
import {api} from '../services/api.js';
import {Card,Loading,ErrorBox,PageHead,DemoTag} from '../components/ui.jsx';
import {SEVERITIES,TYPES} from '../services/mockData.js';
const COLORS=['#16a34a','#84cc16','#f59e0b','#ea580c','#dc2626'],LABELS=['No visible damage','Minor','Moderate','Severe','Critical (engineering review)'];
export default function MapView(){
 const nav=useNavigate();const {data,loading,error,reload}=useAsync(async()=>({a:await api.getAssets(),i:await api.getInspections()}),[]);
 const el=useRef(),map=useRef(),layer=useRef();const [sev,setSev]=useState('');const [type,setType]=useState('');
 useEffect(()=>{
  if(!data||!el.current)return;
  if(!map.current){map.current=L.map(el.current).setView([13.0,80.2],10);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19}).addTo(map.current);layer.current=L.layerGroup().addTo(map.current);}
  layer.current.clearLayers();const pts=[];
  data.a.forEach(a=>{
   if(typeof a.lat!=='number'||typeof a.lng!=='number')return;if(type&&a.type!==type)return;
   const last=data.i.filter(x=>x.assetId===a.id&&x.status==='Completed').sort((p,q)=>q.date.localeCompare(p.date))[0];
   const idx=last?SEVERITIES.indexOf(last.severity):-1;if(sev!==''&&String(idx)!==sev)return;
   const color=idx>=0?COLORS[idx]:'#6b7280';pts.push([a.lat,a.lng]);
   if(idx>=3)L.circle([a.lat,a.lng],{radius:2500,color,fillColor:color,fillOpacity:.15,weight:1,interactive:false}).addTo(layer.current);
   const m=L.circleMarker([a.lat,a.lng],{radius:10,color:'#fff',weight:2,fillColor:color,fillOpacity:.95}).addTo(layer.current);
   const box=document.createElement('div');const t=document.createElement('b');t.textContent=`${a.id} · ${a.name}`;const p=document.createElement('div');p.textContent=`${a.type} · ${a.location}`;
   const s=document.createElement('div');s.textContent=last?`${last.severity} (${last.date})`:'No completed inspection';const b=document.createElement('button');b.textContent='Open asset';b.style.cssText='margin-top:6px;color:#0f5c6e;text-decoration:underline';b.onclick=()=>nav(`/assets/${a.id}`);
   box.append(t,p,s,b);m.bindPopup(box);});
  if(pts.length)map.current.fitBounds(pts,{padding:[40,40],maxZoom:12});
 },[data,sev,type]);// eslint-disable-line
 useEffect(()=>()=>{if(map.current){map.current.remove();map.current=null;}},[]);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error} onRetry={reload}/>;
 return <><PageHead title="Infrastructure damage map" sub="Asset locations with severity-based markers (OpenStreetMap via Leaflet)"><DemoTag text="Sample locations and severities"/></PageHead>
 <Card><div className="mb-3 flex flex-wrap gap-2"><select className="input w-auto" value={type} onChange={e=>setType(e.target.value)}><option value="">All infrastructure types</option>{TYPES.map(t=><option key={t}>{t}</option>)}</select>
 <select className="input w-auto" value={sev} onChange={e=>setSev(e.target.value)}><option value="">All severities</option>{LABELS.map((l,k)=><option key={l} value={k}>{l}</option>)}</select></div>
 <div ref={el} className="z-0 h-[28rem] w-full rounded" role="application" aria-label="Damage map"/>
 <ul className="mt-3 flex flex-wrap gap-4 text-xs">{LABELS.map((l,k)=><li key={l} className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded-full" style={{background:COLORS[k]}}/>{l}</li>)}<li className="flex items-center gap-1"><span className="inline-block h-3 w-3 rounded-full bg-gray-500"/>Not yet inspected</li></ul>
 <p className="mt-2 text-xs text-slate-500">Marker colour is the latest completed inspection severity. Shaded circles mark severe or critical hotspots. Map tiles need an internet connection.</p></Card></>;}
