import {useAsync} from '../hooks/useAsync.js';
import {api} from '../services/api.js';
import {Card,Loading,Empty,ErrorBox,PageHead,Badge,DemoTag,EngineerNotice} from '../components/ui.jsx';
import {PRI_CLS} from '../utils/helpers.js';
import {PRIORITIES} from '../services/mockData.js';
export default function Maintenance(){
 const {data,loading,error,reload}=useAsync(api.getTasks,[]);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error} onRetry={reload}/>;
 const upd=async(id,status)=>{await api.updateTask(id,{status});reload();};
 return <><PageHead title="Maintenance priorities" sub="Tasks derived from inspection findings"><DemoTag/></PageHead>
 <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-5">{PRIORITIES.map(p=><div key={p} className="rounded-lg border border-slate-200 bg-white p-3"><Badge cls={PRI_CLS[p]}>{p}</Badge><div className="mt-1 text-2xl font-semibold">{data.filter(t=>t.priority===p).length}</div></div>)}</div>
 <Card title="Assigned maintenance tasks">{!data.length?<Empty/>:<div className="overflow-x-auto"><table className="w-full"><thead><tr><th>Task</th><th>Asset</th><th>Priority</th><th>Assignee</th><th>Due</th><th>Follow-up inspection</th><th>Status</th></tr></thead><tbody>{data.map(t=><tr key={t.id} className="border-t align-top"><td>{t.title}{t.review&&<div className="text-xs text-red-700">Qualified engineering review required</div>}</td><td>{t.assetId}</td><td><Badge cls={PRI_CLS[t.priority]}>{t.priority}</Badge></td><td>{t.assignee}</td><td>{t.due}</td><td>{t.followUp}</td><td><select className="input w-auto" value={t.status} onChange={e=>upd(t.id,e.target.value)}>{['Open','Assigned','In Progress','Completed'].map(s=><option key={s}>{s}</option>)}</select></td></tr>)}</tbody></table></div>}</Card>
 <div className="mt-4"><EngineerNotice/></div></>;}
