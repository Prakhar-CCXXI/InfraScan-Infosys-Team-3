import {useEffect,useRef} from 'react';
import {Chart,registerables} from 'chart.js';
import {Loader2,Inbox,AlertTriangle,FlaskConical} from 'lucide-react';
Chart.register(...registerables);
export const Badge=({children,cls='bg-slate-100 text-slate-700'})=><span className={`inline-block whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
export const Card=({title,right,children,className=''})=><section className={`rounded-lg border border-slate-200 bg-white ${className}`}>{title&&<div className="flex items-center justify-between border-b border-slate-100 px-4 py-3"><h2 className="text-sm font-semibold">{title}</h2>{right}</div>}<div className="p-4">{children}</div></section>;
export const Field=({label,error,children})=><label className="block text-sm"><span className="mb-1 block font-medium">{label}</span>{children}{error&&<span role="alert" className="mt-1 block text-xs text-red-600">{error}</span>}</label>;
export const Loading=()=><div className="flex items-center gap-2 p-6 text-sm text-slate-500"><Loader2 className="h-4 w-4 animate-spin"/>Loading…</div>;
export const Empty=({text='Nothing to show yet.'})=><div className="flex flex-col items-center gap-2 p-8 text-sm text-slate-500"><Inbox className="h-6 w-6"/>{text}</div>;
export const ErrorBox=({message,onRetry})=><div role="alert" className="flex items-center gap-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertTriangle className="h-4 w-4"/>{message}{onRetry&&<button className="btn-ghost ml-auto" onClick={onRetry}>Retry</button>}</div>;
export const DemoTag=({text='Demo data'})=><span className="inline-flex items-center gap-1 rounded bg-survey/20 px-2 py-0.5 text-xs font-medium text-amber-900"><FlaskConical className="h-3 w-3"/>{text}</span>;
export const PageHead=({title,sub,children})=><div className="mb-4 flex flex-wrap items-end justify-between gap-2"><div><h1 className="text-xl font-semibold">{title}</h1>{sub&&<p className="text-sm text-slate-500">{sub}</p>}</div><div className="flex flex-wrap items-center gap-2">{children}</div></div>;
export const Modal=({title,onClose,children,className=''})=><div className={`fixed inset-0 z-40 flex items-center justify-center bg-ink/50 p-4 ${className}`} role="dialog" aria-modal="true"><div className="max-h-[90vh] w-full max-w-2xl overflow-auto rounded-lg bg-white p-5"><div className="mb-3 flex justify-between"><h2 className="font-semibold">{title}</h2><button onClick={onClose} className="text-slate-500" aria-label="Close">✕</button></div>{children}</div></div>;
export const EngineerNotice=()=><p className="rounded-md border border-survey/50 bg-survey/10 p-3 text-xs text-amber-900">Image-based assessments are decision support only. They are not a structural safety evaluation. Qualified engineering review is required before any safety conclusion.</p>;
export function ChartCanvas({type,data,options}){
 const ref=useRef();
 useEffect(()=>{const c=new Chart(ref.current,{type,data,options:{responsive:true,maintainAspectRatio:false,...options}});return()=>c.destroy();},[type,JSON.stringify(data)]);// eslint-disable-line
 return <div className="h-60"><canvas ref={ref}/></div>;}
