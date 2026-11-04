// Drawn SAMPLE graphics only. No detection happens in the frontend; real images/masks come from the AI module (Part 2).
export default function CrackSvg({mode='original',scale=1}){
 const pts=`20,20 60,70 95,95 130,${150*scale} 175,${170*scale} ${130+80*scale},${150+80*scale}`;
 const mask=mode==='mask';
 return <svg viewBox="0 0 240 260" className="w-full rounded" role="img" aria-label={`Sample ${mode} view of a concrete surface`}>
 <defs><pattern id="conc" width="12" height="12" patternUnits="userSpaceOnUse"><circle cx="3" cy="4" r=".8" fill="#8b929a" opacity=".5"/><circle cx="9" cy="9" r=".6" fill="#8b929a" opacity=".5"/></pattern></defs>
 <rect width="240" height="260" fill={mask?'#0b1117':mode==='pre'?'#e5e7eb':'#c7ccd1'}/>
 {!mask&&<rect width="240" height="260" fill="url(#conc)"/>}
 {!mask&&<line x1="0" y1="215" x2="240" y2="215" stroke="#7b838b" strokeWidth="1.5"/>}
 {mode==='heat'&&<ellipse cx="120" cy="130" rx="70" ry="95" fill="#ef4444" opacity=".35"/>}
 <polyline points={pts} fill="none" stroke={mask?'#fff':mode==='pre'?'#111827':'#4b5563'} strokeWidth={mask?4:2}/>
 {mode==='detect'&&<g><rect x="15" y="15" width="205" height="225" fill="none" stroke="#dc2626" strokeWidth="2"/><text x="19" y="30" fontSize="11" fill="#dc2626">crack 0.91 (sample)</text></g>}
 <text x="6" y="254" fontSize="9" fill={mask?'#9ca3af':'#374151'}>SAMPLE</text></svg>;}
