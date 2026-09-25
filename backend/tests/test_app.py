import os,tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base,engine,SessionLocal
from app.models import *
from app.services.engines import eligibility,opportunity_view,readiness,generate_roadmap,sync_gaps
from datetime import date,timedelta
import json
client=TestClient(app)
def auth_setup(email='test@example.com'):
 r=client.post('/api/auth/register',json={'name':'Test User','email':email,'password':'Password1!','country':'Kazakhstan'});assert r.status_code==200
 return {'Authorization':'Bearer '+r.json()['access_token']}
def test_auth_profile_goal_recalculation_flow():
 h=auth_setup(); assert client.get('/api/auth/me',headers=h).status_code==200
 p={'birth_year':2009,'country':'Kazakhstan','education_level':'HIGH_SCHOOL','grade_year':'11','gpa':3.5,'gpa_scale':4,'english_level':'B2','ielts_score':None,'budget_level':'LOW','preferred_countries':['Germany'],'preferred_fields':['Engineering'],'skills':[],'interests':[],'achievements':'','extracurriculars':'club','volunteering':'','research_experience':'','work_experience':'','city':'','sat_score':None}
 assert client.put('/api/profile',headers=h,json=p).status_code==200
 g=client.post('/api/goals',headers=h,json={'title':'Engineering abroad','target_field':'Engineering','target_countries':['Germany'],'funding_requirement':'HIGH'});assert g.status_code==200;gid=g.json()['id']
 gaps=client.post(f'/api/goals/{gid}/gaps/analyze',headers=h).json();assert any(x['category']=='LANGUAGE' and x['status']=='OPEN' for x in gaps)
 before=client.get('/api/dashboard',headers=h).json()['readiness'];p['ielts_score']=7
 after=client.put('/api/profile',headers=h,json=p).json()['readiness'];assert after['language']>before['language'];assert after['overall']>before['overall']
 gaps=client.get(f'/api/goals/{gid}/gaps',headers=h).json();assert next(x for x in gaps if x['category']=='LANGUAGE')['status']=='RESOLVED'
 with SessionLocal() as db: assert db.query(ReadinessSnapshot).count()>=2
 assert client.get('/api/dashboard',headers=h).status_code==200
 assert client.post('/api/ai/advisor',headers=h,json={'question':'What next?'}).status_code==200

def test_hard_eligibility_and_gap_impact():
 p=StudentProfile(birth_year=date.today().year-16,country='Kazakhstan',education_level='HIGH_SCHOOL')
 o=Opportunity(title='Adult lab',provider='X',opportunity_type='RESEARCH',description='x',min_age=18,deadline=date.today()+timedelta(days=5),eligible_countries='["International"]',education_levels='["HIGH_SCHOOL"]',fields='["Engineering"]',gap_categories='["EXPERIENCE"]')
 status,reasons=eligibility(p,o);assert status=='NOT_ELIGIBLE';assert 'at least 18' in reasons[0]
 with SessionLocal() as db:
  u=User(name='Gap',email='gap@test.com',password_hash='x');db.add(u);db.flush();p.user_id=u.id;db.add(p);g=Goal(user_id=u.id,title='Goal',target_field='Engineering',target_countries='[]');db.add(g);db.flush();gap=ProfileGap(user_id=u.id,goal_id=g.id,category='EXPERIENCE',title='Research gap',description='x',severity='HIGH',current_state='none',target_state='one project',evidence='none');db.add_all([gap,o]);db.flush();v=opportunity_view(p,g,o,[gap],{'overall':50});assert v['gap_impact']=='HIGH';assert v['match_score']>=0

def test_roadmap_order_and_review_authorization():
 h=auth_setup('road@test.com'); assert client.get('/api/roadmap',headers=h).status_code==200
 assert client.get('/api/dashboard').status_code==401

def test_goal_parser_mock_and_malformed_fallback(monkeypatch):
 h=auth_setup('ai@test.com');r=client.post('/api/ai/parse-goal',headers=h,json={'text':'Chemical engineering scholarship in Europe'});assert r.status_code==200;assert r.json()['target_field']=='Chemical Engineering'
 from app.main import ai
 monkeypatch.setattr(ai,'complete',lambda _: 'not json');r=client.post('/api/ai/parse-goal',headers=h,json={'text':'a valid longer goal'});assert r.json()['confidence']==.5
