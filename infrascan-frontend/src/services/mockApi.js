import * as d from './mockData.js';
const wait=(v,ms=400)=>new Promise(r=>setTimeout(()=>r(structuredClone(v)),ms));
let A=[...d.assets],I=[...d.inspections],N=[...d.notifications],T=[...d.tasks];
export const mock={
login:async({email,password,role})=>{if(email==='demo@infrascan.test'&&password==='demo123')return wait({token:'demo-token',user:{name:'Demo User',email,role,demo:true}});throw new Error('Invalid demo credentials. Use demo@infrascan.test / demo123.')},
register:async(u)=>wait({token:'demo-token',user:{name:u.name,email:u.email,role:u.role,department:u.department,demo:true}}),
getAssets:()=>wait(A),getAsset:async(id)=>{const a=A.find(x=>x.id===id);if(!a)throw new Error('Asset not found');return wait(a)},
saveAsset:async(a)=>{if(a.id&&A.some(x=>x.id===a.id))A=A.map(x=>x.id===a.id?{...x,...a}:x);else{a={...a,id:'INF-'+String(A.length+1).padStart(3,'0'),history:[]};A=[...A,a]}return wait(a)},
getInspections:()=>wait(I.map(i=>({images:i.status==='Assigned'?0:3,defects:i.confidence?Math.round(i.confidence*4):0,...i}))),getUsers:()=>wait(d.users),
createInspection:async(i)=>{const n={...i,id:`INS-2026-${String(I.length+1).padStart(3,'0')}`,severity:'—',priority:'—',confidence:null};I=[n,...I];return wait(n)},
uploadImages:async()=>wait({mock:true,message:'Mock mode: no files were sent to any server.'},1200),
getAnalysis:(id)=>wait(d.sampleAnalysis(id)),
getReports:()=>wait(I.filter(i=>i.status!=='Assigned').map(i=>({...i,reportId:'RPT-'+i.id.slice(4),model:'sample-v0'}))),
getTasks:()=>wait(T),updateTask:async(id,p)=>{T=T.map(t=>t.id===id?{...t,...p}:t);return wait(T)},
getNotifications:()=>wait(N),markRead:async(id)=>{N=N.map(n=>id==='all'||n.id===id?{...n,read:true}:n);return wait(N)}};
