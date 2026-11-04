import {Building2,Route,Landmark,Waves,Layers,Mountain,Factory,Construction} from 'lucide-react';
const MAP={Buildings:Building2,Bridges:Landmark,Roads:Route,Tunnels:Construction,Dams:Waves,'Concrete structures':Layers,'Retaining walls':Mountain,'Industrial structures':Factory};
export default function AssetIcon({type,className='h-4 w-4 text-steel'}){const I=MAP[type]||Building2;return <I className={className} aria-label={type}/>;}
