import json,jwt
from datetime import datetime,timedelta,date
from typing import Any
from fastapi import FastAPI,Depends,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel,EmailStr,Field,field_validator
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from sqlalchemy import text,func
from .database import Base,engine,get_db
from .models import *
from .config.settings import settings
from .services.engines import *
from .services.ai import ai
from .services.domains import canonical_domain,detect_opportunity_type,field_relevance,search_matches_domain,clean,requested_domains
from .services.discovery import discover
from .services.reviewer import ApplicationReview,deterministic_review,rubric_for,validate_provider_review
from .services.discovery import discover
Base.metadata.create_all(engine)
app=FastAPI(title='Pathly API',version='1.0.0');app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_url],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
passwords=PasswordHash.recommended();oauth=OAuth2PasswordBearer(tokenUrl='/api/auth/login')
class Register(BaseModel): name:str=Field(min_length=2);email:EmailStr;password:str=Field(min_length=8);country:str=''
class Login(BaseModel): email:EmailStr;password:str
class ProfileIn(BaseModel):
 birth_year:int|None=None;country:str='';city:str='';education_level:str='HIGH_SCHOOL';grade_year:str='';gpa:float|None=None;gpa_scale:float=4;english_level:str='B2';ielts_score:float|None=None;sat_score:int|None=None;budget_level:str='LOW';preferred_countries:list[str]=[];preferred_fields:list[str]=[];skills:list[str]=[];interests:list[str]=[];achievements:str='';projects:str='';extracurriculars:str='';volunteering:str='';research_experience:str='';work_experience:str=''
class GoalIn(BaseModel):
 title:str
 description:str=''
 goal_type:str='UNIVERSITY_ADMISSION'
 target_field:str
 target_countries:list[str]=[]
 target_date:date|None=None
 funding_requirement:str='HIGH'
 education_level:str='BACHELOR'
 language:str='English'

 @field_validator('target_field')
 @classmethod
 def validate_target_field(cls,v:str):
  value=v.strip()
  if not value:
   raise ValueError('Target field is required.')
  if clean(value) in {'bachelor','bachelors','master','masters','phd','doctorate','undergraduate','graduate'}:
   raise ValueError('Target field must be a subject or discipline, not an education level.')
  return canonical_domain(value)
class ParseIn(BaseModel): text:str=Field(min_length=5)
class AdvisorIn(BaseModel): question:str=Field(min_length=2)
class DiscoveryIn(BaseModel): query:str=Field(min_length=3,max_length=300)
class ReviewIn(BaseModel): opportunity_id:int;document_type:str='MOTIVATION_LETTER';title:str='Draft';content:str=Field(min_length=1)
class OnboardingIn(BaseModel): profile:ProfileIn;goal:GoalIn
def token(u):return jwt.encode({'sub':str(u.id),'exp':datetime.utcnow()+timedelta(hours=12)},settings.jwt_secret,algorithm='HS256')
def current(raw:str=Depends(oauth),db:Session=Depends(get_db)):
 try: uid=int(jwt.decode(raw,settings.jwt_secret,algorithms=['HS256'])['sub'])
 except Exception:raise HTTPException(401,'Invalid or expired token')
 u=db.get(User,uid)
 if not u:raise HTTPException(401,'User not found')
 return u
def profile_dict(p):
 d={c.name:getattr(p,c.name) for c in p.__table__.columns}
 for k in ('preferred_countries','preferred_fields','skills','interests'):d[k]=j(d[k])
 return d
def active(db,u):return db.query(Goal).filter_by(user_id=u.id,status='ACTIVE').order_by(Goal.id.desc()).first()
def create_goal_records(db:Session,u:User,x:GoalIn):
 db.query(Goal).filter_by(user_id=u.id,status='ACTIVE').update({'status':'PAUSED'})
 g=Goal(user_id=u.id,**{**x.model_dump(),'target_countries':json.dumps(x.target_countries)});db.add(g);db.flush()
 reqs=[('ACADEMIC','Competitive academic record','Academic expectations vary by selected program','Unknown','GENERAL_GUIDANCE'),('LANGUAGE','English certification guidance','Official English certification may be required; exact target depends on selected programs.','Unknown — select a program for a verified target','GENERAL_GUIDANCE'),('EXPERIENCE','Subject-related experience','Build relevant project or research evidence','Relevant evidence','GENERAL_GUIDANCE'),('APPLICATION','Application narrative','Prepare a tailored motivation letter','Complete draft','GENERAL_GUIDANCE'),('FINANCIAL','Funding plan','Identify sufficient funding','Substantial funding','GOAL_REQUIREMENT')]
 for cat,n,d,t,source in reqs:db.add(Requirement(goal_id=g.id,category=cat,name=n,description=d,target_value=t,source_type=source))
 return g
@app.get('/api/health')
def health(db:Session=Depends(get_db)):
 db.execute(text('select 1'));return {'status':'ok','database':'ok','configured_provider':ai.configured_provider,'active_provider':ai.provider_name,'fallback_used':ai.last_fallback,'ai_provider':ai.provider_name,'demo_ai':ai.provider_name=='mock'}
@app.post('/api/auth/register')
def register(x:Register,db:Session=Depends(get_db)):
 email=str(x.email).strip()
 if db.query(User).filter(func.lower(User.email)==email.lower()).first():raise HTTPException(409,'An account with this email already exists.')
 u=User(name=x.name,email=email,password_hash=passwords.hash(x.password),country=x.country);db.add(u);db.commit();return {'access_token':token(u),'token_type':'bearer','user':{'id':u.id,'name':u.name,'email':u.email}}
@app.post('/api/auth/login')
def login(x:Login,db:Session=Depends(get_db)):
 email=str(x.email).strip()
 u=db.query(User).filter(func.lower(User.email)==email.lower()).first()
 if not u or not passwords.verify(x.password,u.password_hash):raise HTTPException(401,'Incorrect email or password')
 return {'access_token':token(u),'token_type':'bearer','user':{'id':u.id,'name':u.name,'email':u.email}}
@app.get('/api/auth/me')
def me(u=Depends(current)):return {'id':u.id,'name':u.name,'email':u.email,'country':u.country,'role':u.role}
@app.delete('/api/auth/account',status_code=204)
def delete_account(u=Depends(current),db:Session=Depends(get_db)):db.delete(u);db.commit()
@app.get('/api/profile')
def get_profile(u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();return profile_dict(p) if p else None
@app.put('/api/profile')
def put_profile(x:ProfileIn,u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first() or StudentProfile(user_id=u.id)
 for k,v in x.model_dump().items():setattr(p,k,json.dumps(v) if isinstance(v,list) else v)
 db.add(p);goal=active(db,u);db.flush()
 if goal:sync_gaps(db,u.id,goal,p);data=readiness(db,u.id,goal,p)
 else:data=None
 db.commit();return {'profile':profile_dict(p),'readiness':data}
@app.post('/api/ai/parse-goal')
def parse_goal(x:ParseIn,u=Depends(current)):
 try:
  parsed=json.loads(ai.complete('PARSE_GOAL '+x.text))
  field=str(parsed.get('target_field') or '').strip()
  invalid_levels={'bachelor','bachelors','master','masters','phd','doctorate','undergraduate','graduate'}
  if not field or clean(field) in invalid_levels:
   domains=requested_domains(x.text)
   field=domains[0] if domains else 'General'
  else:
   field=canonical_domain(field)
  parsed['target_field']=field
  return {**parsed,'demo_ai':ai.fallback_active}
 except Exception:
  domains=requested_domains(x.text)
  return {'goal_type':'UNIVERSITY_ADMISSION','target_field':domains[0] if domains else 'General','target_regions':[],'language':'English','funding_requirement':'MEDIUM','education_level':'BACHELOR','confidence':.5,'demo_ai':True}
@app.get('/api/goals')
def goals(u=Depends(current),db:Session=Depends(get_db)):return db.query(Goal).filter_by(user_id=u.id).all()
@app.post('/api/goals')
def create_goal(x:GoalIn,u=Depends(current),db:Session=Depends(get_db)):
 g=create_goal_records(db,u,x)
 p=db.query(StudentProfile).filter_by(user_id=u.id).first()
 if p:sync_gaps(db,u.id,g,p);readiness(db,u.id,g,p);generate_roadmap(db,u,g)
 db.commit();return g
@app.post('/api/onboarding/complete')
def complete_onboarding(x:OnboardingIn,u=Depends(current),db:Session=Depends(get_db)):
 """Complete onboarding atomically so a partial path can never reach the dashboard."""
 p=db.query(StudentProfile).filter_by(user_id=u.id).first() or StudentProfile(user_id=u.id)
 for k,v in x.profile.model_dump().items():setattr(p,k,json.dumps(v) if isinstance(v,list) else v)
 db.add(p);db.flush();g=create_goal_records(db,u,x.goal);db.flush()
 sync_gaps(db,u.id,g,p);ready=readiness(db,u.id,g,p);road=generate_roadmap(db,u,g)
 gs=db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all()
 recommendations=[opportunity_view(p,g,o,gs,ready) for o in db.query(Opportunity).all()]
 recommendations=sorted([v for v in recommendations if v['eligibility_status']!='NOT_ELIGIBLE' and v['field_relevance']>=35],key=lambda z:z['match_score'],reverse=True)[:5]
 db.commit();return {'success':True,'goal_id':g.id,'roadmap_id':road.id,'readiness':ready,'recommendations':recommendations}
@app.get('/api/goals/{goal_id}')
def goal(goal_id:int,u=Depends(current),db:Session=Depends(get_db)):
 g=db.get(Goal,goal_id)
 if not g or g.user_id!=u.id:raise HTTPException(404,'Goal not found')
 return g
@app.get('/api/goals/{goal_id}/requirements')
def requirements(goal_id:int,u=Depends(current),db:Session=Depends(get_db)):return db.query(Requirement).filter_by(goal_id=goal_id).all()
@app.post('/api/goals/{goal_id}/gaps/analyze')
def analyze(goal_id:int,u=Depends(current),db:Session=Depends(get_db)):
 g=db.get(Goal,goal_id);p=db.query(StudentProfile).filter_by(user_id=u.id).first()
 if not g or g.user_id!=u.id or not p:raise HTTPException(404,'Profile or goal missing')
 sync_gaps(db,u.id,g,p);db.commit();return db.query(ProfileGap).filter_by(goal_id=g.id).all()
@app.get('/api/goals/{goal_id}/gaps')
def gaps(goal_id:int,u=Depends(current),db:Session=Depends(get_db)):return db.query(ProfileGap).filter_by(user_id=u.id,goal_id=goal_id).all()
@app.get('/api/gaps/{gap_id}')
def gap_detail(gap_id:int,u=Depends(current),db:Session=Depends(get_db)):
 gap=db.get(ProfileGap,gap_id)
 if not gap or gap.user_id!=u.id:raise HTTPException(404,'Gap not found')
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=db.get(Goal,gap.goal_id);ready=readiness(db,u.id,g,p,False)
 related=[]
 for o in db.query(Opportunity).all():
  if gap.category in j(o.gap_categories):related.append(opportunity_view(p,g,o,[gap],ready))
 related.sort(key=lambda z:z['match_score'],reverse=True)
 return {'id':gap.id,'title':gap.title,'category':gap.category,'severity':gap.severity,'why':gap.description,'evidence':gap.evidence,'current_state':gap.current_state,'target_state':gap.target_state,'status':gap.status,'opportunities':related[:6]}
@app.get('/api/opportunities')
def opportunities(search:str='',opportunity_type:str='',country:str='',funding:str='',sort:str='recommended',u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=active(db,u)
 if not p or not g:return []
 gs=db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all();r=readiness(db,u.id,g,p,False);q=db.query(Opportunity); discovery_result=None
 if opportunity_type:q=q.filter_by(opportunity_type=opportunity_type)
 if country:q=q.filter_by(country=country)
 if funding:q=q.filter_by(funding_type=funding)
 records=q.all()
 if search:
  discovery_result=discover(db,search)
  if discovery_result['mode']=='EXTERNAL':
   records=discovery_result['admitted']
  else:
   domains=requested_domains(search);typ=opportunity_type or detect_opportunity_type(search)
   records=[o for o in records if o.source_type=='DEMO' and (not typ or o.opportunity_type==typ) and (not domains or any(field_relevance(d,j(o.fields))>=70 for d in domains))]
 data=[opportunity_view(p,g,o,gs,r) for o in records]
 # Search operates on the eligible universe; recommendation thresholds only shape feeds.
 if search:
  # Explicit search should show qualified source-backed results even when
  # the student's current profile is not eligible. Eligibility is displayed
  # as a personal assessment instead of hiding the opportunity.
  pass
 elif sort=='recommended':data=[x for x in data if x['eligibility_status']!='NOT_ELIGIBLE' and x['field_relevance']>=35]
 key={'readiness':'readiness_score','deadline':'deadline','impact':'gap_impact_score'}.get(sort,'match_score');return sorted(data,key=lambda x:(x[key] is not None,x[key]),reverse=sort!='deadline')
@app.post('/api/opportunities/discover')
def discover_opportunities(x:DiscoveryIn,u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=active(db,u)
 if not p or not g:raise HTTPException(409,'Complete onboarding before discovering opportunities')
 result=discover(db,x.query);gs=db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all();r=readiness(db,u.id,g,p,False)
 records=result.pop('admitted')
 if result['fallback_used']:
  domains=requested_domains(x.query);typ=detect_opportunity_type(x.query)
  records=[o for o in db.query(Opportunity).all() if o.source_type=='DEMO' and (not typ or o.opportunity_type==typ) and (not domains or any(field_relevance(d,j(o.fields))>=70 for d in domains))]
 result['admitted_count']=len(records);result['opportunities']=[opportunity_view(p,g,o,gs,r) for o in records]
 result['no_qualified_results']=result['mode']=='EXTERNAL' and not records
 return result
@app.get('/api/opportunities/{oid}')
def opportunity(oid:int,u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=active(db,u);o=db.get(Opportunity,oid)
 if not o:raise HTTPException(404,'Opportunity not found')
 return opportunity_view(p,g,o,db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all(),readiness(db,u.id,g,p,False))
@app.post('/api/opportunities/{oid}/roadmap')
def add_roadmap(oid:int,u=Depends(current),db:Session=Depends(get_db)):
 o=db.get(Opportunity,oid);g=active(db,u)
 if not o or not g:raise HTTPException(404,'Missing goal or opportunity')
 road=generate_roadmap(db,u,g,o);db.commit();return {'roadmap_id':road.id,'message':'Added to roadmap'}
@app.get('/api/roadmap')
def roadmap(u=Depends(current),db:Session=Depends(get_db)):
 g=active(db,u)
 if not g:return {'roadmap':None,'tasks':[]}
 r=db.query(Roadmap).filter_by(user_id=u.id,goal_id=g.id).first();tasks=db.query(RoadmapTask).filter_by(roadmap_id=r.id).order_by(RoadmapTask.due_date).all() if r else []
 opps={o.id:o for o in db.query(Opportunity).filter(Opportunity.id.in_({t.opportunity_id for t in tasks if t.opportunity_id})).all()}
 return {'roadmap':r,'tasks':[{**{c.name:getattr(t,c.name) for c in t.__table__.columns},'opportunity_title':opps[t.opportunity_id].title if t.opportunity_id in opps else None,'opportunity_deadline':opps[t.opportunity_id].deadline if t.opportunity_id in opps else None} for t in tasks]}
@app.post('/api/goals/{goal_id}/roadmap/generate')
def roadmap_generate(goal_id:int,u=Depends(current),db:Session=Depends(get_db)):
 g=db.get(Goal,goal_id);r=generate_roadmap(db,u,g);db.commit();return r
@app.post('/api/roadmap/tasks/{tid}/complete')
def task_complete(tid:int,u=Depends(current),db:Session=Depends(get_db)):
 t=db.get(RoadmapTask,tid);r=db.get(Roadmap,t.roadmap_id) if t else None
 if not t or r.user_id!=u.id:raise HTTPException(404,'Task not found')
 t.status='COMPLETED';t.completed_at=datetime.utcnow();p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=db.get(Goal,r.goal_id);sync_gaps(db,u.id,g,p);ready=readiness(db,u.id,g,p);db.commit();return {'task':t,'readiness':ready}
@app.get('/api/dashboard')
def dashboard(u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=active(db,u)
 if not p or not g:return {'needs_onboarding':True}
 gs=db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all();r=readiness(db,u.id,g,p,False);opps=[opportunity_view(p,g,o,gs,r) for o in db.query(Opportunity).all()];opps=sorted([v for v in opps if v['eligibility_status']!='NOT_ELIGIBLE' and v['field_relevance']>=35],key=lambda x:x['match_score'],reverse=True)[:5];road=db.query(Roadmap).filter_by(user_id=u.id,goal_id=g.id).first();tasks=db.query(RoadmapTask).filter_by(roadmap_id=road.id).order_by(RoadmapTask.due_date).limit(6).all() if road else [];hist=db.query(ReadinessSnapshot).filter_by(user_id=u.id,goal_id=g.id).order_by(ReadinessSnapshot.created_at).all();return {'user':{'name':u.name},'goal':g,'profile':profile_dict(p),'readiness':r,'gaps':[x for x in gs if x.status!='RESOLVED'],'opportunities':opps,'tasks':tasks,'history':hist,'demo_ai':ai.fallback_active}
def _advisor_answer(raw, candidates, search_intent, domains=None):
 by_id={o['id']:o for o in candidates}
 try:data=json.loads(raw)
 except (TypeError,json.JSONDecodeError):data={'answer':str(raw),'recommendations':[],'general_suggestions':[]}
 answer=str(data.get('answer','')).strip()
 verified=[]
 for item in data.get('recommendations',[]):
  try:opp=by_id.get(int(item.get('id')))
  except (TypeError,ValueError,AttributeError):opp=None
  if opp and opp['id'] not in {x[0]['id'] for x in verified}:
   verified.append((opp,str(item.get('reason','')).strip()))
 if search_intent:
  # Never surface free-form provider text as a stored opportunity fact. The model
  # selects database ids; titles and other facts are rendered exclusively here.
  answer='I searched the source-backed opportunity pipeline.'
  if verified:
   # Provider prose is untrusted too: render only deterministic candidate facts.
   facts=' Matching opportunities: '+'; '.join(f"{opp['title']} ({opp['verification_status']})" for opp,_reason in verified)+'.'
  elif candidates:
   # A malformed provider response cannot erase verified search results.
   facts=' Matching opportunities: '+'; '.join(f"{opp['title']} ({opp['verification_status']})." for opp in candidates[:5])
  else:
   facts=" No matching source-backed opportunity was found. I will not invent one."
  if domains:
   matched={domain for domain in domains if any(field_relevance(domain,opp['fields'])>=70 for opp in candidates)}
   missing=[domain for domain in domains if domain not in matched]
   if missing and matched:
    facts+=f" I found stored {', '.join(sorted(matched))} opportunities, but the current Pathly dataset does not contain a strong {', '.join(missing)} {candidates[0]['type'].lower().replace('_',' ')} match."
  suggestions=[str(x) for x in data.get('general_suggestions',[]) if isinstance(x,str)][:3]
  if suggestions:facts+=' General suggestions (not stored Pathly opportunities): '+'; '.join(suggestions)+'.'
  answer=(answer+' '+facts).strip()
 return answer, [opp['id'] for opp,_ in verified] or ([o['id'] for o in candidates[:5]] if search_intent else [])

@app.post('/api/ai/advisor')
def advisor(x:AdvisorIn,u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=active(db,u)
 if not p or not g:raise HTTPException(409,'Complete onboarding before using the advisor')
 question=x.question.lower();requested_type=detect_opportunity_type(question);domains=requested_domains(question)
 opportunity_words=('opportunit','olympiad','competition','scholarship','program','extracurricular')
 search_intent=any(term in question for term in ('find','search','recommend','show me')) or ('do i have' in question and any(term in question for term in opportunity_words)) or 'which opportunity' in question
 discovery_state=None;external_candidate_ids=None
 if search_intent and settings.opportunity_discovery_provider.lower()=='serper':
  discovery_state=discover(db,x.question)
  if discovery_state['mode']=='EXTERNAL':external_candidate_ids={o.id for o in discovery_state['admitted']}
 gs=db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all();r=readiness(db,u.id,g,p,False);road=db.query(Roadmap).filter_by(user_id=u.id,goal_id=g.id).first()
 tasks=db.query(RoadmapTask).filter_by(roadmap_id=road.id).all() if road else []
 requirements=db.query(Requirement).filter_by(goal_id=g.id).all()
 all_opps=db.query(Opportunity).all();views=[opportunity_view(p,g,o,gs,r) for o in all_opps]
 context={'user':{'id':u.id,'name':u.name},'profile':profile_dict(p),'goal':{'id':g.id,'title':g.title,'field':g.target_field,'funding':g.funding_requirement,'countries':j(g.target_countries),'education_level':g.education_level,'language':g.language},'requirements':[{'category':z.category,'name':z.name,'target':z.target_value,'source_type':z.source_type} for z in requirements],'open_gaps':[{'title':z.title,'category':z.category,'severity':z.severity,'current_state':z.current_state,'target_state':z.target_state,'evidence':z.evidence} for z in gs if z.status=='OPEN'],'resolved_gaps':[{'title':z.title,'category':z.category} for z in gs if z.status=='RESOLVED'],'readiness':r,'roadmap':{'title':road.title if road else None,'tasks':[{'title':z.title,'status':z.status,'due_date':str(z.due_date),'opportunity_id':z.opportunity_id} for z in tasks]}}
 requested_fields=domains or [g.target_field]
 requested_gap='EXTRACURRICULAR' if 'extracurricular' in question else None
 candidates=[]
 for opp,view in zip(all_opps,views):
  if external_candidate_ids is not None and opp.id not in external_candidate_ids:continue
  # For explicit external searches, search relevance takes priority over the
  # user's active goal. Keep a source-backed result even when the active goal
  # makes its personal eligibility/match low; the UI can still show that
  # personal assessment separately.
  if external_candidate_ids is None and view['eligibility_status']=='NOT_ELIGIBLE':continue
  relevance=max(field_relevance(field,j(opp.fields)) for field in requested_fields)
  if search_intent and relevance<70:continue
  if requested_type and opp.opportunity_type!=requested_type:continue
  if requested_gap and requested_gap not in j(opp.gap_categories):continue
  if opp.verification_status not in ('VERIFIED','SOURCE_FOUND','DEMO'):continue
  candidates.append({'id':opp.id,'title':opp.title,'provider':opp.provider,'type':opp.opportunity_type,'fields':j(opp.fields),'gap_categories':j(opp.gap_categories),'field_relevance':relevance,'match_score':view['match_score'],'eligibility':view['eligibility_status'],'gap_impact':view['gap_impact'],'deadline':str(opp.deadline) if opp.deadline else None,'source_url':opp.source_url,'source_label':opp.source_label,'verification_status':opp.verification_status})
 candidates.sort(key=lambda z:(z['field_relevance'],z['match_score']),reverse=True);candidates=candidates[:8]
 prompt={'instructions':['Answer the question using only this authenticated user context.','Return JSON with answer, recommendations [{id, reason}], and general_suggestions.','Recommendation ids must come from candidate_opportunities. Do not put opportunity names, URLs, eligibility, or deadlines in answer; the server renders stored facts.','General suggestions must be activity categories, never invented named opportunities, and must be clearly non-Pathly.'],'question':x.question,'context':context,'candidate_opportunities':candidates}
 try:raw=ai.complete('ADVISOR_JSON '+json.dumps(prompt, default=str))
 except Exception:raw=ai.mock.complete('ADVISOR_JSON '+json.dumps(prompt, default=str));ai.last_fallback=True;ai.last_active_provider='mock'
 answer,ids=_advisor_answer(raw,candidates,search_intent,requested_fields if domains else None)
 selected=[opportunity_view(p,g,o,gs,r) for o in all_opps if o.id in ids]
 response={'answer':answer,'intent':'OPPORTUNITY_SEARCH' if search_intent else 'GUIDANCE','opportunity_ids':ids,'opportunities':selected,'demo_ai':ai.fallback_active,'ai_provider':ai.provider_name}
 if discovery_state:
  response['discovery']={'mode':discovery_state['mode'],'fallback_used':discovery_state['fallback_used'],'error':discovery_state['error'],'raw_result_count':discovery_state['raw_result_count'],'rejected_count':discovery_state['rejected_count'],'admitted_count':len(discovery_state['admitted']),'no_qualified_results':discovery_state['mode']=='EXTERNAL' and not discovery_state['admitted']}
 return response
@app.post('/api/applications/review')
def review(x:ReviewIn,u=Depends(current),db:Session=Depends(get_db)):
 opp=db.get(Opportunity,x.opportunity_id)
 if not opp:raise HTTPException(404,'Opportunity not found')
 doc=ApplicationDocument(user_id=u.id,**x.model_dump());db.add(doc);db.flush()
 payload={'opportunity_type':opp.opportunity_type,'requirements':opp.requirements_text,'document_type':x.document_type,'content':x.content,'instructions':'No evidence means no credit. Evidence must be an exact quote from content. Return the required JSON schema only.','criteria':[name for name,_ in rubric_for(opp.opportunity_type,opp.requirements_text)],'json_schema':ApplicationReview.model_json_schema()}
 baseline=deterministic_review(opp.opportunity_type,opp.requirements_text,x.content)
 if baseline.review_status=='INSUFFICIENT_CONTENT':data=baseline
 else:
  data=None
  for _ in range(2 if ai.configured_real else 1):
   try:data=validate_provider_review(ai.complete('REVIEW_JSON '+json.dumps(payload)),x.content,set(payload['criteria']));break
   except Exception:continue
  if data is None:data=baseline;ai.last_fallback=ai.configured_real;ai.last_active_provider='mock'
 serialized=data.model_dump()
 coverage={criterion['criterion']:criterion['score'] for criterion in serialized['criteria']}
 rev=DocumentReview(document_id=doc.id,overall_score=serialized['overall_score'] or 0,requirement_coverage=json.dumps(coverage),strengths=json.dumps(serialized['strengths']),gaps=json.dumps(serialized['missing_evidence']),recommendations=json.dumps(serialized['recommendations']));db.add(rev);g=active(db,u);p=db.query(StudentProfile).filter_by(user_id=u.id).first()
 if g and p:sync_gaps(db,u.id,g,p);readiness(db,u.id,g,p)
 db.commit();return {**serialized,'id':rev.id,'demo_ai':ai.provider_name=='mock','ai_provider':ai.provider_name}
@app.get('/api/applications/reviews')
def reviews(u=Depends(current),db:Session=Depends(get_db)):return db.query(DocumentReview).join(ApplicationDocument).filter(ApplicationDocument.user_id==u.id).all()
