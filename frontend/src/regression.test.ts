import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import{renderToStaticMarkup}from'react-dom/server';
import{api,formatApiError}from'./api.ts';
import{destinationAfterAuthentication,establishSession}from'./auth.ts';
import{ReadinessCard}from'./readiness.ts';

class MemoryStorage{
 private values=new Map<string,string>();
 getItem(key:string){return this.values.get(key)??null}
 setItem(key:string,value:string){this.values.set(key,String(value))}
 removeItem(key:string){this.values.delete(key)}
 clear(){this.values.clear()}
 get length(){return this.values.size}
 key(index:number){return [...this.values.keys()][index]??null}
}

test('registration response establishes a session and routes to onboarding',()=>{
 Object.defineProperty(globalThis,'localStorage',{value:new MemoryStorage(),configurable:true});
 establishSession({access_token:'new-user-token',token_type:'bearer'});
 assert.equal(localStorage.getItem('token'),'new-user-token');
 assert.equal(destinationAfterAuthentication(true),'/onboarding');
 assert.notEqual(destinationAfterAuthentication(true),'/login');
});

test('the newly registered token is sent to an authenticated endpoint',async()=>{
 Object.defineProperty(globalThis,'localStorage',{value:new MemoryStorage(),configurable:true});
 establishSession({access_token:'own-registration-token'});
 let authorization='';
 globalThis.fetch=async(_input,init)=>{
  authorization=new Headers(init?.headers).get('Authorization')??'';
  return new Response(JSON.stringify({id:42}),{status:200,headers:{'Content-Type':'application/json'}});
 };
 await api('/auth/me');
 assert.equal(authorization,'Bearer own-registration-token');
});

test('FastAPI email validation errors are human-readable',()=>{
 const message=formatApiError({detail:[{type:'value_error',loc:['body','email'],msg:'value is not a valid email address: The part after the @-sign is not valid.'}]});
 assert.equal(message,'Enter a valid email address.');
 assert.doesNotMatch(message,/\[object Object\]/);
 assert.equal(formatApiError({detail:{reason:{message:'Account could not be created'}}}),'Account could not be created');
});

test('overall readiness card renders the backend value and qualification',()=>{
 const html=renderToStaticMarkup(React.createElement(ReadinessCard,{readiness:{overall:69.5}}));
 assert.match(html,/OVERALL READINESS/);
 assert.match(html,/69\.5%/);
 assert.match(html,/Preparedness heuristic/);
});
