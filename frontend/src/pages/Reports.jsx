import {useState} from 'react';
import {Printer,FileDown} from 'lucide-react';
import {useAsync} from '../hooks/useAsync.js';
import {api} from '../services/api.js';
import {Card,Loading,Empty,ErrorBox,PageHead,Badge,DemoTag,Modal,EngineerNotice} from '../components/ui.jsx';
import CrackSvg from '../components/CrackSvg.jsx';
import {SEV_CLS,PRI_CLS,download,toCsv} from '../utils/helpers.js';
export default function Reports(){
 const {data,loading,error,reload}=useAsync(async()=>({r:await api.getReports(),a:await api.getAssets(),n:await api.getAnalysis('sample')}),[]);
 const [q,setQ]=useState('');const [sev,setSev]=useState('');const [sel,setSel]=useState(null);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error} onRetry={reload}/>;
 const rows=data.r.filter(r=>(!sev||r.severity===sev)&&(r.reportId+r.assetId+r.inspector).toLowerCase().includes(q.toLowerCase()));
 const asset=sel&&data.a.find(x=>x.id===sel.assetId)||{};const c=data.n.cracks[0];
 const print=()=>{document.body.classList.add('print-report');window.print();document.body.classList.remove('print-report');};
 return <><PageHead title="Inspection reports" sub="View, print and export"><DemoTag text="Demo reports"/><button className="btn-ghost" onClick={()=>download('infrascan-reports.csv',toCsv(rows),'text/csv')}><FileDown className="h-4 w-4"/>Export list as CSV</button></PageHead>
 <Card><div className="mb-3 flex flex-wrap gap-2"><input className="input w-56" placeholder="Search report, asset, inspector" value={q} onChange={e=>setQ(e.target.value)}/><select className="input w-auto" value={sev} onChange={e=>setSev(e.target.value)}><option value="">All severities</option>{[...new Set(data.r.map(r=>r.severity))].map(s=><option key={s}>{s}</option>)}</select></div>
 {!rows.length?<Empty text="No reports match your filters."/>:<div className="overflow-x-auto"><table className="w-full"><thead><tr><th>Report</th><th>Infrastructure</th><th>Date</th><th>Severity</th><th>Priority</th><th></th></tr></thead><tbody>{rows.map(r=><tr key={r.reportId} className="border-t"><td>{r.reportId}</td><td>{r.assetId}</td><td>{r.date}</td><td><Badge cls={SEV_CLS[r.severity]}>{r.severity}</Badge></td><td><Badge cls={PRI_CLS[r.priority]}>{r.priority}</Badge></td><td><button className="btn-ghost" onClick={()=>setSel(r)}>Open</button></td></tr>)}</tbody></table></div>}</Card>
 {sel&&<Modal className="rp" title={`Inspection report ${sel.reportId}`} onClose={()=>setSel(null)}>
 <h3 className="mb-1 text-sm font-semibold">Inspection and infrastructure</h3>
 <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">{[['Inspection ID',sel.id],['Infrastructure ID',sel.assetId],['Infrastructure name',asset.name],['Infrastructure type',asset.type],['Location',asset.location],['Inspection date',sel.date],['Inspector',sel.inspector]].map(([k,v])=><div key={k} className="contents"><dt className="text-slate-500">{k}</dt><dd>{v}</dd></div>)}</dl>
 <h3 className="mb-1 mt-4 text-sm font-semibold">Images <DemoTag text="Sample graphics"/></h3>
 <div className="grid grid-cols-3 gap-2"><figure><CrackSvg mode="original"/><figcaption className="text-center text-xs">Original</figcaption></figure><figure><CrackSvg mode="detect"/><figcaption className="text-center text-xs">Detected crack</figcaption></figure><figure><CrackSvg mode="heat"/><figcaption className="text-center text-xs">Analysis visualization</figcaption></figure></div>
 <h3 className="mb-1 mt-4 text-sm font-semibold">Findings</h3>
 <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">{[['Detected crack',c.type],['Length',`${c.lengthPx} px`],['Average / max width',`${c.avgWidthPx} / ${c.maxWidthPx} px`],['Damage category',data.n.surfaceDamage[0].category],['Severity',sel.severity],['AI confidence',sel.confidence?Math.round(sel.confidence*100)+'%':'—'],['Maintenance priority',sel.priority],['Model version',sel.model],['Engineer review status',sel.status==='Completed'?'Reviewed':'Pending engineer review']].map(([k,v])=><div key={k} className="contents"><dt className="text-slate-500">{k}</dt><dd>{v}</dd></div>)}</dl>
 <div className="my-3"><EngineerNotice/></div><p className="mb-3 text-xs text-slate-500">Frontend demo only: findings shown are sample values and measurements are uncalibrated pixels. PDF uses your browser's print dialog ("Save as PDF"). Server-side PDF/Excel generation (Part 4) is not connected.</p>
 <div className="no-print flex flex-wrap gap-2"><button className="btn" onClick={print}><Printer className="h-4 w-4"/>Print / Save as PDF</button><button className="btn-ghost" onClick={()=>download(sel.reportId+'.csv',toCsv([sel]),'text/csv')}>CSV</button><button className="btn-ghost" onClick={()=>download(sel.reportId+'.json',JSON.stringify(sel,null,2),'application/json')}>JSON</button></div></Modal>}</>;}
