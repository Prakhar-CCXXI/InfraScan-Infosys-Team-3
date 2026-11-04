export default function Hero(){
 const cable=(tx)=>[1,2,3,4,5,6].flatMap(k=>[tx-k*22,tx+k*22]).map(x=><line key={tx+'-'+x} x1={tx} y1="34" x2={x} y2="120" stroke="#9aa5ae" strokeWidth="1"/>);
 return <div className="hidden flex-1 flex-col justify-between bg-[#1d3140] p-10 text-slate-100 lg:flex">
 <div><h1 className="max-w-md text-3xl font-semibold leading-tight">Find the crack before it becomes the repair.</h1>
 <p className="mt-3 max-w-md text-slate-300">Inspect bridges, roads, tunnels, dams and buildings. Review AI crack detection and damage assessment, with an engineer in the loop.</p></div>
 <svg viewBox="0 0 600 220" className="w-full" aria-hidden="true">
  <rect y="165" width="600" height="55" fill="#0f1b24"/><rect y="116" width="600" height="8" fill="#9aa5ae"/>
  <rect x="150" y="30" width="10" height="135" fill="#9aa5ae"/><rect x="440" y="30" width="10" height="135" fill="#9aa5ae"/>
  {cable(155)}{cable(445)}
  <polyline points="154,130 158,142 153,150 159,160" fill="none" stroke="#e8a317" strokeWidth="2"/>
 </svg>
 <p className="text-xs text-slate-400">InfraScan · AI-Powered Crack &amp; Damage Assessment for Civil Infrastructure</p></div>;}
