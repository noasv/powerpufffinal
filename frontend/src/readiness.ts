import React from 'react';

export type ReadinessData={overall?:number;overall_readiness?:number};

export function overallReadiness(readiness:ReadinessData):number|null{
 const value=readiness?.overall??readiness?.overall_readiness;
 return typeof value==='number'&&Number.isFinite(value)?value:null;
}

export function ReadinessCard({readiness}:{readiness:ReadinessData}){
 const value=overallReadiness(readiness);
 return React.createElement('div',{className:'card bg-ink text-white',style:{backgroundColor:'#0B1F3A',color:'#fff'},'data-testid':'overall-readiness'},
  React.createElement('small',null,'OVERALL READINESS'),
  React.createElement('div',{className:'mt-2 text-5xl font-black'},value===null?'Not available':`${value}%`),
  React.createElement('p',{className:'mt-2 text-sm text-white/75'},'Preparedness heuristic based on your current profile — not admission probability.')
 );
}
