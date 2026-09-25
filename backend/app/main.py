import json,jwt
from datetime import datetime,timedelta,date
from typing import Any
from fastapi import FastAPI,Depends,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel,EmailStr,Field
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from sqlalchemy import text
from .database import Base,engine,get_db
from .models import *
from .config.settings import settings
from .services.engines import *
from .services.ai import ai
Base.metadata.create_all(engine)
app=FastAPI(title='Pathly API',version='1.0.0');app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_url],allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
passwords=PasswordHash.recommended();oauth=OAuth2PasswordBearer(tokenUrl='/api/auth/login')
class Register(BaseModel): name:str=Field(min_length=2);email:EmailStr;password:str=Field(min_length=8);country:str=''
class Login(BaseModel): email:EmailStr;password:str
class ProfileIn(BaseModel):
 birth_year:int|None=None;country:str='';city:str='';education_level:str='HIGH_SCHOOL';grade_year:str='';gpa:float|None=None;gpa_scale:float=4;english_level:str='B2';ielts_score:float|None=None;sat_score:int|None=None;budget_level:str='LOW';preferred_countries:list[str]=[];preferred_fields:list[str]=[];skills:list[str]=[];interests:list[str]=[];achievements:str='';extracurriculars:str='';volunteering:str='';research_experience:str='';work_experience:str=''
class GoalIn(BaseModel): title:str;description:str='';goal_type:str='UNIVERSITY_ADMISSION';target_field:str='';target_countries:list[str]=[];target_date:date|None=None;funding_requirement:str='HIGH';education_level:str='BACHELOR';language:str='English'
class ParseIn(BaseModel): text:str=Field(min_length=5)
class AdvisorIn(BaseModel): question:str=Field(min_length=2)
class ReviewIn(BaseModel): opportunity_id:int;document_type:str='MOTIVATION_LETTER';title:str='Draft';content:str=Field(min_length=20)
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
@app.get('/api/health')
def health(db:Session=Depends(get_db)):
 db.execute(text('select 1'));return {'status':'ok','database':'ok','ai_provider':'mock' if ai.fallback_active else settings.ai_provider,'demo_ai':ai.fallback_active}
@app.post('/api/auth/register')
def register(x:Register,db:Session=Depends(get_db)):
 if db.query(User).filter_by(email=x.email.lower()).first():raise HTTPException(409,'Email already registered')
 u=User(name=x.name,email=x.email.lower(),password_hash=passwords.hash(x.password),country=x.country);db.add(u);db.commit();return {'access_token':token(u),'token_type':'bearer','user':{'id':u.id,'name':u.name,'email':u.email}}
@app.post('/api/auth/login')
def login(x:Login,db:Session=Depends(get_db)):
 u=db.query(User).filter_by(email=x.email.lower()).first()
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
 try:return {**json.loads(ai.complete('PARSE_GOAL '+x.text)),'demo_ai':ai.fallback_active}
 except Exception:return {'goal_type':'UNIVERSITY_ADMISSION','target_field':'General Studies','target_regions':[],'language':'English','funding_requirement':'MEDIUM','education_level':'BACHELOR','confidence':.5,'demo_ai':True}
@app.get('/api/goals')
def goals(u=Depends(current),db:Session=Depends(get_db)):return db.query(Goal).filter_by(user_id=u.id).all()
@app.post('/api/goals')
def create_goal(x:GoalIn,u=Depends(current),db:Session=Depends(get_db)):
 db.query(Goal).filter_by(user_id=u.id,status='ACTIVE').update({'status':'PAUSED'});g=Goal(user_id=u.id,**{**x.model_dump(),'target_countries':json.dumps(x.target_countries)});db.add(g);db.flush()
 reqs=[('ACADEMIC','Competitive academic record','Maintain evidence of strong relevant coursework','3.2 GPA'),('LANGUAGE','Certified English proficiency','Provide recognized English test evidence','IELTS 6.5'),('EXPERIENCE','Subject-related experience','Build a project or research experience','1 project'),('APPLICATION','Application narrative','Prepare a tailored motivation letter','Complete draft'),('FINANCIAL','Funding plan','Identify sufficient funding','Substantial funding')]
 for cat,n,d,t in reqs:db.add(Requirement(goal_id=g.id,category=cat,name=n,description=d,target_value=t))
 p=db.query(StudentProfile).filter_by(user_id=u.id).first()
 if p:sync_gaps(db,u.id,g,p);readiness(db,u.id,g,p);generate_roadmap(db,u,g)
 db.commit();return g
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
@app.get('/api/opportunities')
def opportunities(search:str='',opportunity_type:str='',country:str='',funding:str='',sort:str='recommended',u=Depends(current),db:Session=Depends(get_db)):
 p=db.query(StudentProfile).filter_by(user_id=u.id).first();g=active(db,u)
 if not p or not g:return []
 gs=db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all();r=readiness(db,u.id,g,p,False);q=db.query(Opportunity)
 if search:q=q.filter((Opportunity.title.ilike(f'%{search}%'))|(Opportunity.provider.ilike(f'%{search}%'))|(Opportunity.description.ilike(f'%{search}%')))
 if opportunity_type:q=q.filter_by(opportunity_type=opportunity_type)
 if country:q=q.filter_by(country=country)
 if funding:q=q.filter_by(funding_type=funding)
 data=[opportunity_view(p,g,o,gs,r) for o in q.all()]
 key={'readiness':'readiness_score','deadline':'deadline','impact':'gap_impact'}.get(sort,'match_score');return sorted(data,key=lambda x:(x[key] is not None,x[key]),reverse=sort!='deadline')
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
 r=db.query(Roadmap).filter_by(user_id=u.id,goal_id=g.id).first();tasks=db.query(RoadmapTask).filter_by(roadmap_id=r.id).order_by(RoadmapTask.due_date).all() if r else [];return {'roadmap':r,'tasks':tasks}
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
 gs=db.query(ProfileGap).filter_by(user_id=u.id,goal_id=g.id).all();r=readiness(db,u.id,g,p,False);opps=[opportunity_view(p,g,o,gs,r) for o in db.query(Opportunity).all()];opps=sorted(opps,key=lambda x:x['match_score'],reverse=True)[:5];road=db.query(Roadmap).filter_by(user_id=u.id,goal_id=g.id).first();tasks=db.query(RoadmapTask).filter_by(roadmap_id=road.id).order_by(RoadmapTask.due_date).limit(6).all() if road else [];hist=db.query(ReadinessSnapshot).filter_by(user_id=u.id,goal_id=g.id).order_by(ReadinessSnapshot.created_at).all();return {'goal':g,'profile':profile_dict(p),'readiness':r,'gaps':[x for x in gs if x.status!='RESOLVED'],'opportunities':opps,'tasks':tasks,'history':hist,'demo_ai':ai.fallback_active}
@app.post('/api/ai/advisor')
def advisor(x:AdvisorIn,u=Depends(current),db:Session=Depends(get_db)):return {'answer':ai.complete('ADVISOR '+x.question),'demo_ai':ai.fallback_active}
@app.post('/api/applications/review')
def review(x:ReviewIn,u=Depends(current),db:Session=Depends(get_db)):
 if not db.get(Opportunity,x.opportunity_id):raise HTTPException(404,'Opportunity not found')
 doc=ApplicationDocument(user_id=u.id,**x.model_dump());db.add(doc);db.flush()
 try:data=json.loads(ai.complete('REVIEW '+x.content))
 except:data=json.loads(ai.mock.complete('REVIEW '+x.content))
 rev=DocumentReview(document_id=doc.id,overall_score=data['overall_score'],requirement_coverage=json.dumps(data['requirement_coverage']),strengths=json.dumps(data['strengths']),gaps=json.dumps(data['gaps']),recommendations=json.dumps(data['recommendations']));db.add(rev);g=active(db,u);p=db.query(StudentProfile).filter_by(user_id=u.id).first();sync_gaps(db,u.id,g,p);readiness(db,u.id,g,p);db.commit();return {**data,'id':rev.id,'demo_ai':ai.fallback_active}
@app.get('/api/applications/reviews')
def reviews(u=Depends(current),db:Session=Depends(get_db)):return db.query(DocumentReview).join(ApplicationDocument).filter(ApplicationDocument.user_id==u.id).all()
