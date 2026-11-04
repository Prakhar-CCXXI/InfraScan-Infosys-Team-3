import {useEffect,useRef,useState} from 'react';
import {Modal} from './ui.jsx';
import {RotateCcw,RotateCw} from 'lucide-react';
// Rotates (90° steps) and center-crops an image on a canvas; returns a new File to the caller.
function render(img,rot,ratio){
 const r=((rot%360)+360)%360,sw=r%180?img.naturalHeight:img.naturalWidth,sh=r%180?img.naturalWidth:img.naturalHeight;
 const c=document.createElement('canvas');c.width=sw;c.height=sh;const x=c.getContext('2d');x.translate(sw/2,sh/2);x.rotate(r*Math.PI/180);x.drawImage(img,-img.naturalWidth/2,-img.naturalHeight/2);
 if(ratio==='free')return c;const [rw,rh]=ratio.split(':').map(Number);let cw=sw,ch=sw*rh/rw;if(ch>sh){ch=sh;cw=sh*rw/rh;}
 const o=document.createElement('canvas');o.width=Math.round(cw);o.height=Math.round(ch);o.getContext('2d').drawImage(c,(sw-cw)/2,(sh-ch)/2,cw,ch,0,0,o.width,o.height);return o;}
export default function ImageEditor({item,onApply,onClose}){
 const cv=useRef(),img=useRef(new Image());const [ready,setReady]=useState(false);const [rot,setRot]=useState(0);const [ratio,setRatio]=useState('free');
 useEffect(()=>{img.current.onload=()=>setReady(true);img.current.src=item.url;},[item.url]);
 useEffect(()=>{if(!ready)return;const o=render(img.current,rot,ratio);cv.current.width=o.width;cv.current.height=o.height;cv.current.getContext('2d').drawImage(o,0,0);},[ready,rot,ratio]);
 const apply=()=>cv.current.toBlob(b=>onApply(new File([b],item.file.name.replace(/\.\w+$/,'')+'-edited.jpg',{type:'image/jpeg'})),'image/jpeg',0.92);
 return <Modal title="Crop or rotate image" onClose={onClose}>
  <canvas ref={cv} className="mx-auto max-h-72 w-full rounded bg-slate-100 object-contain"/>
  <div className="mt-3 flex flex-wrap items-center gap-2"><button type="button" className="btn-ghost" aria-label="Rotate left" onClick={()=>setRot(rot-90)}><RotateCcw className="h-4 w-4"/></button><button type="button" className="btn-ghost" aria-label="Rotate right" onClick={()=>setRot(rot+90)}><RotateCw className="h-4 w-4"/></button>
  <select className="input w-auto" value={ratio} onChange={e=>setRatio(e.target.value)}><option value="free">No crop</option><option value="1:1">Center crop 1:1</option><option value="4:3">Center crop 4:3</option><option value="16:9">Center crop 16:9</option></select></div>
  <div className="mt-4 flex justify-end gap-2"><button type="button" className="btn-ghost" onClick={onClose}>Cancel</button><button type="button" className="btn" disabled={!ready} onClick={apply}>Apply</button></div></Modal>;}
