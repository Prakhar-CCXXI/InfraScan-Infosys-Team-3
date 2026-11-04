import {Bell} from 'lucide-react';
import {useAsync} from '../hooks/useAsync.js';
import {api} from '../services/api.js';
import {Card,Loading,Empty,ErrorBox,PageHead,Badge,DemoTag} from '../components/ui.jsx';
const LV={Informational:'bg-slate-100 text-slate-700',Low:'bg-sky-100 text-sky-800',Medium:'bg-amber-100 text-amber-800',High:'bg-orange-100 text-orange-800',Critical:'bg-red-100 text-red-800'};
export default function Notifications(){
 const {data,loading,error,reload}=useAsync(api.getNotifications,[]);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error} onRetry={reload}/>;
 const read=async id=>{await api.markRead(id);reload();};
 return <><PageHead title="Notifications" sub="Alerts about inspections and findings"><DemoTag text="Demo notifications"/><button className="btn-ghost" onClick={()=>read('all')}>Mark all read</button></PageHead>
 <Card>{!data.length?<Empty text="You're all caught up."/>:<ul className="divide-y">{data.map(n=><li key={n.id} className={`flex items-start gap-3 py-3 ${n.read?'opacity-60':''}`}><Bell className="mt-1 h-4 w-4 text-steel"/><div className="flex-1 text-sm"><div className="flex flex-wrap items-center gap-2"><b>{n.type}</b><Badge cls={LV[n.level]}>{n.level}</Badge><span className="text-xs text-slate-500">{n.time}</span></div><p>{n.text}</p></div>{!n.read&&<button className="btn-ghost" onClick={()=>read(n.id)}>Mark read</button>}</li>)}</ul>}</Card></>;}
