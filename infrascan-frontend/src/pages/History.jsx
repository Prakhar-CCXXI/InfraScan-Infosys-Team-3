import {useState} from 'react';
import {useAsync} from '../hooks/useAsync.js';
import {api} from '../services/api.js';
import {Card,Loading,Empty,ErrorBox,PageHead,Badge,DemoTag,ChartCanvas} from '../components/ui.jsx';
import CrackSvg from '../components/CrackSvg.jsx';
import {SEV_CLS} from '../utils/helpers.js';
import {SEVERITIES} from '../services/mockData.js';
export default function History(){
 const {data,loading,error,reload}=useAsync(async()=>({i:await api.getInspections(),a:await api.getAssets()}),[]);const [aid,setAid]=useState('INF-001');
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error} onRetry={reload}/>;
 const rows=data.i.filter(x=>x.assetId===aid&&x.status==='Completed').sort((a,b)=>a.date.localeCompare(b.date));
 return <><PageHead title="Inspection history" sub="Previous inspections and damage progression"><DemoTag text="Demo records"/>
 <select className="input w-auto" value={aid} onChange={e=>setAid(e.target.value)}>{data.a.map(a=><option key={a.id} value={a.id}>{a.id} · {a.name}</option>)}</select></PageHead>
 {!rows.length?<Empty text="No completed inspections for this asset."/>:<>
 <div className="grid gap-4 lg:grid-cols-2"><Card title="Severity trend"><ChartCanvas type="line" options={{scales:{y:{min:0,max:4,ticks:{stepSize:1,callback:v=>['None','Minor','Moderate','Severe','Critical'][v]}}},plugins:{legend:{display:false}}}} data={{labels:rows.map(r=>r.date),datasets:[{data:rows.map(r=>SEVERITIES.indexOf(r.severity)),borderColor:'#0f5c6e',tension:.2}]}}/></Card>
 <Card title="Timeline"><table className="w-full"><thead><tr><th>Date</th><th>Inspection</th><th>Severity</th></tr></thead><tbody>{rows.map(r=><tr key={r.id} className="border-t"><td>{r.date}</td><td>{r.id}</td><td><Badge cls={SEV_CLS[r.severity]}>{r.severity}</Badge></td></tr>)}</tbody></table></Card></div>
 <Card title="Previous vs current image" className="mt-4"><div className="grid max-w-xl grid-cols-2 gap-3"><figure><CrackSvg scale={0.8}/><figcaption className="text-center text-xs">Previous · {rows[0].date}</figcaption></figure><figure><CrackSvg scale={1.1}/><figcaption className="text-center text-xs">Current · {rows[rows.length-1].date}</figcaption></figure></div>
 <p className="mt-2 text-xs text-slate-500">Sample graphics. Reliable progression needs comparable viewpoints, calibrated scale and image registration from the AI module.</p></Card></>}</>;}
