// DEMO DATA ONLY. Replaced by real responses once Part 3 (backend) is connected.
export const SEVERITIES=['No Visible Damage','Minor Damage','Moderate Damage','Severe Damage','Critical / Requires Urgent Engineering Review'];
export const PRIORITIES=['Routine Monitoring','Low Priority','Medium Priority','High Priority','Urgent Engineering Review'];
export const TYPES=['Buildings','Bridges','Roads','Tunnels','Dams','Concrete structures','Retaining walls','Industrial structures'];
export const ROLES=['Civil Engineer','Infrastructure Inspector','Maintenance Engineer','Infrastructure Manager','Administrator'];
export const assets=[
{id:'INF-001',name:'Marina Flyover',type:'Bridges',location:'Chennai, TN',lat:13.05,lng:80.28,year:1998,material:'Prestressed concrete',department:'Highways Dept.',frequency:'6 months',history:['2021: Expansion joint replaced','2024: Deck resurfacing']},
{id:'INF-002',name:'Adyar Retaining Wall B',type:'Retaining walls',location:'Adyar, Chennai',lat:13.0,lng:80.25,year:2005,material:'Reinforced concrete',department:'Public Works',frequency:'12 months',history:['2022: Drainage repaired']},
{id:'INF-003',name:'Metro Tunnel Section 4',type:'Tunnels',location:'Anna Salai, Chennai',lat:13.06,lng:80.26,year:2014,material:'Segmental lining',department:'Metro Rail',frequency:'3 months',history:[]},
{id:'INF-004',name:'OMR Road Segment 12',type:'Roads',location:'OMR, Chennai',lat:12.9,lng:80.23,year:2011,material:'Asphalt',department:'Highways Dept.',frequency:'6 months',history:['2023: Pothole patching']},
{id:'INF-005',name:'Pallikaranai Admin Block',type:'Buildings',location:'Pallikaranai',lat:12.94,lng:80.21,year:2009,material:'RCC frame',department:'Municipal Corp.',frequency:'12 months',history:[]},
{id:'INF-006',name:'Poondi Reservoir Dam',type:'Dams',location:'Tiruvallur Dist.',lat:13.2,lng:79.9,year:1944,material:'Masonry/concrete',department:'Water Resources',frequency:'3 months',history:['2019: Spillway gate overhaul']}];
export const inspections=[
{id:'INS-2026-001',assetId:'INF-001',date:'2026-10-02',inspector:'R. Kumar',status:'Completed',severity:'Moderate Damage',priority:'Medium Priority',confidence:0.91},
{id:'INS-2026-002',assetId:'INF-002',date:'2026-09-18',inspector:'S. Priya',status:'Completed',severity:'Severe Damage',priority:'High Priority',confidence:0.87},
{id:'INS-2026-003',assetId:'INF-003',date:'2026-10-15',inspector:'R. Kumar',status:'Pending Review',severity:'Minor Damage',priority:'Low Priority',confidence:0.83},
{id:'INS-2026-004',assetId:'INF-004',date:'2026-10-28',inspector:'A. Fathima',status:'Assigned',severity:'—',priority:'—',confidence:null},
{id:'INS-2026-005',assetId:'INF-006',date:'2026-10-30',inspector:'S. Priya',status:'Assigned',severity:'—',priority:'—',confidence:null},
{id:'INS-2026-006',assetId:'INF-001',date:'2026-04-05',inspector:'R. Kumar',status:'Completed',severity:'Minor Damage',priority:'Routine Monitoring',confidence:0.89},
{id:'INS-2026-007',assetId:'INF-002',date:'2026-03-12',inspector:'S. Priya',status:'Completed',severity:'Moderate Damage',priority:'Medium Priority',confidence:0.85},
{id:'INS-2025-008',assetId:'INF-001',date:'2025-10-01',inspector:'A. Fathima',status:'Completed',severity:'No Visible Damage',priority:'Routine Monitoring',confidence:0.94}];
export const tasks=[
{id:'MT-101',assetId:'INF-002',title:'Seal and monitor wall cracks',priority:'High Priority',status:'In Progress',assignee:'M. Arun',due:'2026-11-05',followUp:'2026-12-01',review:true},
{id:'MT-102',assetId:'INF-001',title:'Deck crack injection',priority:'Medium Priority',status:'Assigned',assignee:'M. Arun',due:'2026-11-20',followUp:'2027-01-10',review:false},
{id:'MT-103',assetId:'INF-003',title:'Lining joint re-check',priority:'Low Priority',status:'Open',assignee:'T. Selvi',due:'2026-12-15',followUp:'2027-01-15',review:false},
{id:'MT-104',assetId:'INF-006',title:'Spillway surface survey',priority:'Urgent Engineering Review',status:'Open',assignee:'Unassigned',due:'2026-10-27',followUp:'2026-11-10',review:true}];
export const notifications=[
{id:1,type:'Severe damage identified',level:'High',text:'INF-002: severe damage flagged. Qualified engineering review required.',time:'2h ago',read:false},
{id:2,type:'Inspection assigned',level:'Informational',text:'INS-2026-004 assigned to A. Fathima.',time:'5h ago',read:false},
{id:3,type:'Maintenance deadline approaching',level:'Medium',text:'MT-104 is due in 4 days.',time:'1d ago',read:false},
{id:4,type:'Report generated',level:'Informational',text:'Report for INS-2026-001 is ready.',time:'2d ago',read:true},
{id:5,type:'Engineering review required',level:'Critical',text:'INF-006: urgent review requested. This is not a safety declaration.',time:'3d ago',read:true},
{id:6,type:'Damage detected',level:'Low',text:'INS-2026-003: minor surface cracking detected.',time:'4d ago',read:true},
{id:7,type:'Maintenance task assigned',level:'Low',text:'MT-103 assigned to T. Selvi.',time:'5d ago',read:true},
{id:8,type:'Follow-up inspection required',level:'Medium',text:'INF-002: follow-up inspection due 2026-12-01.',time:'6d ago',read:true}];
export const users=[{name:'R. Kumar',role:'Infrastructure Inspector'},{name:'S. Priya',role:'Infrastructure Inspector'},{name:'A. Fathima',role:'Infrastructure Inspector'},{name:'M. Arun',role:'Maintenance Engineer'},{name:'Dr. L. Venkat',role:'Civil Engineer'}];
export const sampleAnalysis=(id)=>({inspectionId:id,sample:true,modelVersion:'sample-v0 (no real model)',
cracks:[{id:1,type:'Diagonal crack',confidence:0.91,lengthPx:412,avgWidthPx:5.2,maxWidthPx:9.1,areaPx:2140,orientationDeg:47}],
surfaceDamage:[{category:'Water leakage/staining',confidence:0.74}],crackDensityPct:1.8,calibrated:false,
severity:'Moderate Damage',priority:'Medium Priority',reviewStatus:'Pending engineer review',explainability:true});
