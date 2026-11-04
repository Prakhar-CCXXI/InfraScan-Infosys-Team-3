import {useState} from 'react';
import {useParams,Link} from 'react-router-dom';
import {useAsync} from '../hooks/useAsync.js';
import {api} from '../services/api.js';
import {Card,Loading,ErrorBox,PageHead,Badge,DemoTag,EngineerNotice} from '../components/ui.jsx';
import CrackSvg from '../components/CrackSvg.jsx';
import {SEV_CLS,PRI_CLS} from '../utils/helpers.js';
export default function Results(){
 const {id='INS-2026-001'}=useParams();const {data,loading,error,reload}=useAsync(()=>api.getAnalysis(id),[id]);const [review,setReview]=useState(null);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error} onRetry={reload}/>;
 const c=data.cracks[0];const unit=data.calibrated?'mm':'px';
 const steps=[['Original image','original'],['Preprocessed image','pre'],['Crack bounding boxes','detect'],['Segmentation mask','mask'],['Damage assessment','heat']];
 return <><PageHead title="Damage analysis" sub={`Inspection ${data.inspectionId} · model ${data.modelVersion}`}>{data.sample&&<DemoTag text="Sample results, not real AI output"/>}<Link to={`/inspections/${data.inspectionId}`} className="btn-ghost">Inspection</Link></PageHead>
 <Card title="Comparison view: Original ↔ Crack detection ↔ Segmentation mask ↔ Damage assessment (preprocessed image shown for reference)"><div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{steps.map(([l,m],i)=><figure key={m}><CrackSvg mode={m}/><figcaption className="mt-1 text-center text-xs text-slate-600">{i+1}. {l}{m==='heat'&&' (explainability overlay, if provided)'}</figcaption></figure>)}</div></Card>
 <div className="mt-4 grid gap-4 lg:grid-cols-3">
 <Card title="Crack measurements"><table className="w-full text-sm"><tbody>{[['Type',c.type],['Length',`${c.lengthPx} ${unit}`],['Average width',`${c.avgWidthPx} ${unit}`],['Maximum width',`${c.maxWidthPx} ${unit}`],['Area',`${c.areaPx} ${unit}²`],['Orientation',`${c.orientationDeg}°`],['Crack density',`${data.crackDensityPct}%`]].map(([k,v])=><tr key={k} className="border-t"><td className="text-slate-500">{k}</td><td>{v}</td></tr>)}</tbody></table>
  {!data.calibrated&&<p className="mt-2 text-xs text-slate-500">No scale calibration available, so values are in pixels, not physical units.</p>}</Card>
 <Card title="Classification"><ul className="space-y-2 text-sm"><li>Crack confidence: <b>{Math.round(c.confidence*100)}%</b></li>{data.surfaceDamage.map(s=><li key={s.category}>{s.category}: <b>{Math.round(s.confidence*100)}%</b></li>)}<li>Severity: <Badge cls={SEV_CLS[data.severity]}>{data.severity}</Badge></li><li>Suggested priority: <Badge cls={PRI_CLS[data.priority]}>{data.priority}</Badge></li></ul></Card>
 <Card title="Engineer review"><p className="mb-2 text-sm">Status: <b>{review||data.reviewStatus}</b></p><div className="flex flex-wrap gap-2"><button className="btn" onClick={()=>setReview('Confirmed by engineer (local demo state)')}>Confirm</button><button className="btn-ghost" onClick={()=>setReview('Engineering review requested (local demo state)')}>Request review</button></div></Card></div>
 <div className="mt-4"><EngineerNotice/></div></>;}
