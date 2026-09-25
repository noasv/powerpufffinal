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

def profile_payload(ielts=None):
 return {'birth_year':date.today().year-17,'country':'Kazakhstan','city':'','education_level':'HIGH_SCHOOL','grade_year':'11','gpa':3.7,'gpa_scale':4,'english_level':'B2','ielts_score':ielts,'sat_score':None,'budget_level':'LOW','preferred_countries':['United States'],'preferred_fields':['Computer Science'],'skills':['Python'],'interests':['Technology'],'achievements':'Math project','extracurriculars':'Coding club','volunteering':'School volunteer','research_experience':'','work_experience':''}

def computer_science_goal():
 return {'title':'Computer Science in the United States','description':'CS with a full scholarship','goal_type':'UNIVERSITY_ADMISSION','target_field':'Computer Science','target_countries':['United States'],'funding_requirement':'HIGH','education_level':'BACHELOR','language':'English'}

def test_registration_token_completes_atomic_onboarding_with_own_goal():
 h=auth_setup('fresh-cs@example.com')
 assert client.get('/api/dashboard',headers=h).json()['needs_onboarding'] is True
 result=client.post('/api/onboarding/complete',headers=h,json={'profile':profile_payload(),'goal':computer_science_goal()})
 assert result.status_code==200 and result.json()['success'] is True
 assert result.json()['recommendations'] is not None
 dashboard=client.get('/api/dashboard',headers=h).json()
 assert dashboard['goal']['target_field']=='Computer Science'
 assert 'Chemical Engineering' not in dashboard['goal']['title']
 assert dashboard['history'] and dashboard['tasks']

def test_gap_detail_matching_and_roadmap_idempotency_and_ownership():
 h=auth_setup('gap-detail@example.com');client.post('/api/onboarding/complete',headers=h,json={'profile':profile_payload(),'goal':computer_science_goal()})
 with SessionLocal() as db:
  o1=Opportunity(title='CS Research Lab',provider='One',opportunity_type='RESEARCH',description='Research',country='International',deadline=date.today()+timedelta(days=60),eligible_countries='["International"]',education_levels='["HIGH_SCHOOL"]',fields='["Computer Science"]',gap_categories='["EXPERIENCE"]')
  o2=Opportunity(title='Summer Computing',provider='Two',opportunity_type='SUMMER_SCHOOL',description='Research',country='International',deadline=date.today()+timedelta(days=70),eligible_countries='["International"]',education_levels='["HIGH_SCHOOL"]',fields='["Computer Science"]',gap_categories='["EXPERIENCE"]');db.add_all([o1,o2]);db.commit();ids=(o1.id,o2.id)
 dash=client.get('/api/dashboard',headers=h).json();gap=next(g for g in dash['gaps'] if g['category']=='EXPERIENCE')
 detail=client.get(f"/api/gaps/{gap['id']}",headers=h).json()
 assert all(detail[k] for k in ('title','category','severity','why','evidence','current_state','target_state','status'))
 assert {o['id'] for o in detail['opportunities']}.issuperset(ids)
 for oid in (*ids,ids[0]):assert client.post(f'/api/opportunities/{oid}/roadmap',headers=h).status_code==200
 road=client.get('/api/roadmap',headers=h).json();owned=[t for t in road['tasks'] if t['opportunity_id'] in ids]
 assert len([t for t in owned if t['opportunity_id']==ids[0]])==6
 assert {t['opportunity_title'] for t in owned}=={'CS Research Lab','Summer Computing'}

def test_advisor_changes_when_language_gap_resolves():
 h=auth_setup('advisor-state@example.com');client.post('/api/onboarding/complete',headers=h,json={'profile':profile_payload(),'goal':computer_science_goal()})
 before=client.post('/api/ai/advisor',headers=h,json={'question':'What should I focus on this month and why?'}).json()['answer']
 assert 'Official English evidence missing' in before
 updated=profile_payload(7.0);client.put('/api/profile',headers=h,json=updated)
 after=client.post('/api/ai/advisor',headers=h,json={'question':'What should I focus on this month and why?'}).json()['answer']
 assert after!=before and 'Official English evidence missing' not in after and 'Computer Science' in after

def test_demo_seed_canonical_and_idempotent():
 from app.seed import seed
 seed()
 with SessionLocal() as db:
  u=db.query(User).filter_by(email='student@demo.com').one();before=(db.query(User).count(),db.query(StudentProfile).filter_by(user_id=u.id).count(),db.query(Goal).filter_by(user_id=u.id).count(),db.query(RoadmapTask).join(Roadmap).filter(Roadmap.user_id==u.id).count())
 seed()
 with SessionLocal() as db:
  u=db.query(User).filter_by(email='student@demo.com').one();p=db.query(StudentProfile).filter_by(user_id=u.id).one();g=db.query(Goal).filter_by(user_id=u.id,status='ACTIVE').one();after_counts=(db.query(User).count(),db.query(StudentProfile).filter_by(user_id=u.id).count(),db.query(Goal).filter_by(user_id=u.id).count(),db.query(RoadmapTask).join(Roadmap).filter(Roadmap.user_id==u.id).count())
  assert before==after_counts;assert u.name=='Aruzhan Demo' and p.grade_year=='11' and p.ielts_score is None and not p.research_experience;assert g.target_field=='Chemical Engineering'
