const BASE=import.meta.env?.VITE_API_URL||'http://localhost:8000';

type ValidationIssue={loc?:unknown[];msg?:unknown;message?:unknown;detail?:unknown};

function collectMessages(value:unknown,locations:string[]=[]):string[]{
 if(typeof value==='string')return [value];
 if(Array.isArray(value))return value.flatMap(item=>collectMessages(item,locations));
 if(value&&typeof value==='object'){
  const issue=value as ValidationIssue;
  const loc=Array.isArray(issue.loc)?issue.loc.map(String):locations;
  const message=typeof issue.msg==='string'?issue.msg:typeof issue.message==='string'?issue.message:null;
  if(message){
   if(loc.some(part=>part.toLowerCase()==='email')&&/email|address|valid/i.test(message))return ['Enter a valid email address.'];
   const fields=loc.filter(part=>!['body','query','path'].includes(part));
   const field=fields[fields.length-1]?.replaceAll('_',' ');
   return [field?`${field[0].toUpperCase()+field.slice(1)}: ${message}`:message];
  }
  if('detail'in issue)return collectMessages(issue.detail,loc);
  return Object.values(value).flatMap(item=>collectMessages(item,loc));
 }
 return [];
}

/** Converts API, validation, and network failures into text that is safe to render. */
export function formatApiError(error:unknown,fallback='Something went wrong. Please try again.'):string{
 if(error instanceof Error)return error.message||fallback;
 const messages=collectMessages(error);
 return messages.length?[...new Set(messages)].join(' '):fallback;
}

export async function api<T>(path:string,options:RequestInit={}):Promise<T>{
 const token=localStorage.getItem('token');
 let r:Response;
 try{r=await fetch(BASE+'/api'+path,{...options,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}) ,...options.headers}})}
 catch(error){throw new Error(formatApiError(error,'Unable to connect. Check your connection and try again.'))}
 if(!r.ok){
  let body:unknown;
  try{body=await r.json()}catch{body=undefined}
  throw new Error(formatApiError(body,`Request failed (${r.status}).`));
 }
 if(r.status===204)return undefined as T;
 return r.json();
}

/** Ensures an interactive request cannot leave the UI pending forever. */
export async function apiWithTimeout<T>(path:string,options:RequestInit={},timeoutMs=20_000):Promise<T>{
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),timeoutMs);
 try{return await api<T>(path,{...options,signal:controller.signal})}
 catch(error){
  if(controller.signal.aborted)throw new Error('The advisor took too long to respond. Please try again.');
  throw error;
 }finally{clearTimeout(timer)}
}
export type Opportunity={id:number;title:string;provider:string;opportunity_type:string;description:string;country:string;funding_type:string;deadline:string;match_score:number;readiness_score:number;gap_impact:string;eligibility_status:string;explanation:string;impacts:{title:string;strength:string;reason:string}[];official_url:string;source_label:string;requirements_text:string;eligibility_reasons:string[]}
