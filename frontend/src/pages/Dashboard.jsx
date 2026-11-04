import {Link} from 'react-router-dom';
import {useAsync} from '../hooks/useAsync.js';
import {useAuth} from '../hooks/useAuth.jsx';
import {api} from '../services/api.js';
import {Card,Loading,ErrorBox,PageHead,DemoTag,Badge,ChartCanvas,Empty} from '../components/ui.jsx';
import {SEV_CLS,STATUS_CLS,PRI_CLS} from '../utils/helpers.js';
import {SEVERITIES,PRIORITIES} from '../services/mockData.js';
const Stats=({items})=><div className="grid grid-cols-2 gap-3 lg:grid-cols-5">{items.map(([l,v])=><div key={l} className="rounded-lg border border-slate-200 border-l-4 border-l-survey bg-white p-3"><div className="text-2xl font-semibold">{v}</div><div className="text-xs text-slate-500">{l}</div></div>)}</div>;
const InspTable=({rows,action})=>!rows.length?<Empty text="No inspections here."/>:<div className="overflow-x-auto"><table className="w-full"><thead><tr><th>ID</th><th>Infrastructure</th><th>Date</th><th>Status</th><th>Severity</th><th>Defects</th>{action&&<th></th>}</tr></thead><tbody>{rows.map(x=><tr key={x.id} className="border-t"><td><Link className="text-steel underline" to={`/inspections/${x.id}`}>{x.id}</Link></td><td>{x.assetId}</td><td>{x.date}</td><td><Badge cls={STATUS_CLS[x.status]}>{x.status}</Badge></td><td><Badge cls={SEV_CLS[x.severity]}>{x.severity}</Badge></td><td>{x.defects}</td>{action&&<td><Link className="btn-ghost" to={action[0]}>{action[1]}</Link></td>}</tr>)}</tbody></table></div>;
const Pending=({text})=><Card title={text}><Empty text="Provided by another module and not connected yet."/></Card>;
export default function Dashboard(){
 const {user}=useAuth();
 const {data,loading,error,reload}=useAsync(async()=>{const[a,i,t,u]=await Promise.all([api.getAssets(),api.getInspections(),api.getTasks(),api.getUsers()]);return{a,i,t,u};},[]);
 if(loading)return <Loading/>;if(error)return <ErrorBox message={error} onRetry={reload}/>;
 const {a,i,t,u}=data;const role=user.role;const done=i.filter(x=>x.status==='Completed'),pend=i.filter(x=>x.status!=='Completed');
 const idx=x=>SEVERITIES.indexOf(x.severity);const sum=k=>i.reduce((s,x)=>s+(x[k]||0),0);
 const byMonth=(rows,fn)=>{const m={};rows.forEach(r=>{(m[r.date.slice(0,7)]=m[r.date.slice(0,7)]||[]).push(r);});const ks=Object.keys(m).sort();return{labels:ks,values:ks.map(k=>fn(m[k]))};};
 const cond=byMonth(done,r=>+(r.reduce((s,x)=>s+idx(x),0)/r.length).toFixed(2)),trend=byMonth(done.filter(x=>idx(x)>=2),r=>r.length);
 const sevChart=<Card title="Damage severity distribution"><ChartCanvas type="bar" options={{plugins:{legend:{display:false}}}} data={{labels:['None','Minor','Moderate','Severe','Critical'],datasets:[{data:SEVERITIES.map(s=>i.filter(x=>x.severity===s).length),backgroundColor:'#0f5c6e'}]}}/></Card>;
 const taskBy=(k,vals)=>vals.map(v=>t.filter(x=>x[k]===v).length);
 const maint=<Card title="Maintenance progress"><ChartCanvas type="bar" options={{indexAxis:'y',plugins:{legend:{display:false}}}} data={{labels:['Open','Assigned','In Progress','Completed'],datasets:[{data:taskBy('status',['Open','Assigned','In Progress','Completed']),backgroundColor:'#16232e'}]}}/></Card>;
 const latest=aid=>done.filter(x=>x.assetId===aid).sort((p,q)=>q.date.localeCompare(p.date))[0];
 const hot=a.filter(x=>{const l=latest(x.id);return l&&idx(l)>=2;});
 const hi=i.filter(x=>['High Priority','Urgent Engineering Review'].includes(x.priority));
 let head,body;
 if(role==='Infrastructure Inspector'){head='Inspector dashboard';body=<><Stats items={[['Assigned inspections',i.filter(x=>['Assigned','In Progress'].includes(x.status)).length],['Pending inspections',pend.length],['Uploaded images',sum('images')],['Detected defects',sum('defects')],['Completed inspections',done.length]]}/>
  <Card className="mt-4" title="Assigned and pending inspections"><InspTable rows={pend} action={['/upload','Upload images']}/></Card><Card className="mt-4" title="Inspection history"><InspTable rows={done}/></Card></>;}
 else if(role==='Civil Engineer'){const conf=done.filter(x=>x.confidence);head='Civil engineer dashboard';body=<><Stats items={[['Inspections analysed',done.length],['Avg. AI confidence (sample)',conf.length?Math.round(conf.reduce((s,x)=>s+x.confidence,0)/conf.length*100)+'%':'—'],['Severe or critical findings',i.filter(x=>idx(x)>=3).length],['Awaiting engineer review',i.filter(x=>x.status==='Pending Review').length],['Reports available',done.length+i.filter(x=>x.status==='Pending Review').length]]}/>
  <div className="mt-4 grid gap-4 lg:grid-cols-3">{sevChart}<Card title="Infrastructure condition history (0 none – 4 critical)"><ChartCanvas type="line" options={{plugins:{legend:{display:false}},scales:{y:{min:0,max:4}}}} data={{labels:cond.labels,datasets:[{data:cond.values,borderColor:'#e8a317',tension:.3}]}}/></Card>
  <Card title="Latest AI prediction" right={<DemoTag text="Sample result"/>}><p className="text-sm">Diagonal crack, confidence 91%. Length 412 px, max width 9.1 px (uncalibrated).</p><Link to="/results" className="btn mt-3">Open damage analysis</Link></Card></div>
  <Card className="mt-4" title="Recent inspections"><InspTable rows={i.slice(0,5)}/></Card></>;}
 else if(role==='Maintenance Engineer'){head='Maintenance dashboard';body=<><Stats items={[['Open tasks',t.filter(x=>x.status==='Open').length],['Assigned',t.filter(x=>x.status==='Assigned').length],['In progress',t.filter(x=>x.status==='In Progress').length],['Urgent engineering review',t.filter(x=>x.priority===PRIORITIES[4]).length],['Follow-up inspections',t.filter(x=>x.followUp).length]]}/>
  <div className="mt-4 grid gap-4 lg:grid-cols-2">{maint}<Card title="Tasks by priority"><ChartCanvas type="bar" options={{plugins:{legend:{display:false}}}} data={{labels:['Routine','Low','Medium','High','Urgent'],datasets:[{data:taskBy('priority',PRIORITIES),backgroundColor:'#0f5c6e'}]}}/></Card></div>
  <Card className="mt-4" title="My maintenance tasks" right={<Link className="btn-ghost" to="/maintenance">Open maintenance</Link>}><table className="w-full"><thead><tr><th>Task</th><th>Asset</th><th>Priority</th><th>Due</th><th>Status</th></tr></thead><tbody>{t.map(x=><tr key={x.id} className="border-t"><td>{x.title}</td><td>{x.assetId}</td><td><Badge cls={PRI_CLS[x.priority]}>{x.priority}</Badge></td><td>{x.due}</td><td>{x.status}</td></tr>)}</tbody></table></Card></>;}
 else if(role==='Infrastructure Manager'){head='Infrastructure manager dashboard';body=<><Stats items={[['Total infrastructure assets',a.length],['Total inspections',i.length],['Damaged assets',new Set(done.filter(x=>idx(x)>=2).map(x=>x.assetId)).size],['High-priority findings',hi.length],['Open maintenance tasks',t.filter(x=>x.status!=='Completed').length]]}/>
  <div className="mt-4 grid gap-4 lg:grid-cols-3">{maint}<Card title="Damage trends (moderate or worse findings per month)"><ChartCanvas type="line" options={{plugins:{legend:{display:false}}}} data={{labels:trend.labels,datasets:[{data:trend.values,borderColor:'#dc2626',tension:.3}]}}/></Card>
  <Card title="Geographic hotspots" right={<Link className="btn-ghost" to="/map">Open map</Link>}>{hot.length?<ul className="space-y-1 text-sm">{hot.map(x=><li key={x.id}>{x.name} <Badge cls={SEV_CLS[latest(x.id).severity]}>{latest(x.id).severity}</Badge></li>)}</ul>:<Empty/>}</Card></div></>;}
 else{head='Administrator dashboard';body=<><Stats items={[['Infrastructure records',a.length],['Inspections',i.length],['Users (sample)',u.length],['Maintenance tasks',t.length]]}/>
  <div className="mt-4 grid gap-4 lg:grid-cols-2"><Card title="User management" right={<DemoTag text="Sample users"/>}><ul className="text-sm">{u.map(x=><li key={x.name} className="flex justify-between border-t py-1"><span>{x.name}</span><span className="text-slate-500">{x.role}</span></li>)}</ul></Card>
  <Card title="Infrastructure records" right={<Link className="btn-ghost" to="/assets">Manage</Link>}><p className="text-sm">{a.length} assets registered across {new Set(a.map(x=>x.type)).size} infrastructure types.</p></Card>
  <Pending text="Model performance"/><Pending text="System activity and audit logs"/><Pending text="Platform health"/></div></>;}
 return <><PageHead title={head} sub="Infrastructure inspection overview"><DemoTag/></PageHead>{body}</>;}
