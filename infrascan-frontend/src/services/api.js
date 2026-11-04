// Single integration point. Set VITE_API_BASE_URL to use real endpoints (paths below are PROPOSED; align with Part 3).
import {mock} from './mockApi.js';
const BASE=import.meta.env.VITE_API_BASE_URL;
export const isMock=!BASE;
async function http(path,{method='GET',body}={}){
 const form=body instanceof FormData;
 const res=await fetch(BASE+path,{method,headers:{...(form?{}:{'Content-Type':'application/json'}),Authorization:`Bearer ${localStorage.getItem('infrascan_token')||''}`},body:form?body:body&&JSON.stringify(body)});
 if(!res.ok)throw new Error(`Request failed (${res.status})`);return res.json();}
const use=(real,fake)=>isMock?fake():real();
export const api={
 login:c=>use(()=>http('/auth/login',{method:'POST',body:c}),()=>mock.login(c)),
 register:u=>use(()=>http('/auth/register',{method:'POST',body:u}),()=>mock.register(u)),
 getAssets:()=>use(()=>http('/assets'),mock.getAssets),
 getAsset:id=>use(()=>http(`/assets/${id}`),()=>mock.getAsset(id)),
 saveAsset:a=>use(()=>http(a.id?`/assets/${a.id}`:'/assets',{method:a.id?'PUT':'POST',body:a}),()=>mock.saveAsset(a)),
 getUsers:()=>use(()=>http('/users'),mock.getUsers),
 getInspections:()=>use(()=>http('/inspections'),mock.getInspections),
 createInspection:i=>use(()=>http('/inspections',{method:'POST',body:i}),()=>mock.createInspection(i)),
 uploadImages:fd=>use(()=>http('/images/upload',{method:'POST',body:fd}),()=>mock.uploadImages(fd)),
 getAnalysis:id=>use(()=>http(`/inspections/${id}/analysis`),()=>mock.getAnalysis(id)),
 getReports:()=>use(()=>http('/reports'),mock.getReports),
 getTasks:()=>use(()=>http('/maintenance/tasks'),mock.getTasks),
 updateTask:(id,p)=>use(()=>http(`/maintenance/tasks/${id}`,{method:'PATCH',body:p}),()=>mock.updateTask(id,p)),
 getNotifications:()=>use(()=>http('/notifications'),mock.getNotifications),
 markRead:id=>use(()=>http(`/notifications/${id}/read`,{method:'POST'}),()=>mock.markRead(id))};
