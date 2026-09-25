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

def test_auth_email_format_duplicate_and_enumeration_safety():
 invalid=['zhans@aya','test@','@test.com','test.com','test@.com','test@example.','test@@example.com','user name@example.com','@example.com']
 for email in invalid:
  assert client.post('/api/auth/register',json={'name':'Test User','email':email,'password':'Password1!','country':'Kazakhstan'}).status_code==422
  assert client.post('/api/auth/login',json={'email':email,'password':'Password1!'}).status_code==422
 for i,email in enumerate(['student@example.com','name.surname@gmail.com','student123@school.edu','user+pathly@example.org']):
  assert client.post('/api/auth/register',json={'name':'Test User','email':email,'password':'Password1!','country':'Kazakhstan'}).status_code==200
 duplicate=client.post('/api/auth/register',json={'name':'Test User','email':'student@example.com','password':'Password1!','country':'Kazakhstan'})
 assert duplicate.status_code==409 and duplicate.json()['detail']=='An account with this email already exists.'
 unknown=client.post('/api/auth/login',json={'email':'unknown@example.com','password':'Password1!'})
 wrong=client.post('/api/auth/login',json={'email':'student@example.com','password':'WrongPassword!'})
 assert unknown.status_code==wrong.status_code==401
 assert unknown.json()['detail']==wrong.json()['detail']=='Incorrect email or password'
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

def no_experience_profile():
 return StudentProfile(birth_year=date.today().year-17,country='Kazakhstan',education_level='HIGH_SCHOOL',gpa=3.9,gpa_scale=4,english_level='B2',budget_level='LOW',projects='',research_experience='',work_experience='',extracurriculars='',volunteering='',achievements='')

def test_readiness_uses_independent_evidence_categories():
 with SessionLocal() as db:
  u=User(name='Evidence',email='evidence@test.com',password_hash='x');db.add(u);db.flush();p=no_experience_profile();p.user_id=u.id;db.add(p);g=Goal(user_id=u.id,title='Economics',target_field='Economics',funding_requirement='HIGH');db.add(g);db.flush()
  empty=readiness(db,u.id,g,p,False);assert empty['experience']<=20 and empty['extracurricular']<=20
  p.projects='Econometrics analysis project';project=readiness(db,u.id,g,p,False);assert project['experience']>empty['experience'] and project['extracurricular']==empty['extracurricular'] and project['academic']==empty['academic']
  p.projects='';p.research_experience='Research assistant on an economics study';research=readiness(db,u.id,g,p,False);assert research['experience']>empty['experience']
  p.research_experience='';p.volunteering='Food bank volunteer';volunteer=readiness(db,u.id,g,p,False);assert volunteer['extracurricular']>empty['extracurricular'] and volunteer['experience']==empty['experience'] and volunteer['language']==empty['language']

def test_normalized_field_ranking_and_gap_specific_impact():
 p=no_experience_profile();g=Goal(title='Economics abroad',target_field='Economics',target_countries='[]',funding_requirement='HIGH')
 gap=ProfileGap(id=100,category='EXPERIENCE',title='Research evidence',severity='HIGH',status='OPEN')
 def opp(title,typ,fields,cats,restricted=False):return Opportunity(id=100+len(title),title=title,provider='Demo',opportunity_type=typ,description='demo',fields=json.dumps(fields),gap_categories=json.dumps(cats),eligible_countries='["International"]',education_levels='["HIGH_SCHOOL"]',field_restriction=restricted,funding_type='FULL',country='International')
 econ=opportunity_view(p,g,opp('Economics Olympiad','COMPETITION',['Economics'],['EXPERIENCE']),[gap],{'overall':20})
 general=opportunity_view(p,g,opp('General Scholarship','SCHOLARSHIP',['General'],['FINANCIAL']),[gap],{'overall':20})
 chemistry=opportunity_view(p,g,opp('Chemistry Degree','UNIVERSITY_PROGRAM',['Chemistry'],['ACADEMIC'],True),[gap],{'overall':20})
 finance=opportunity_view(p,g,opp('Finance Challenge','COMPETITION',['Finance'],['EXPERIENCE']),[gap],{'overall':20})
 assert econ['match_score']>finance['match_score']>chemistry['match_score'];assert finance['field_relevance']==70
 assert econ['match_score']>general['match_score']>chemistry['match_score'];assert econ['gap_impact']=='HIGH' and chemistry['gap_impact']=='LOW';assert chemistry['eligibility_status']=='NOT_ELIGIBLE'
 chem_goal=Goal(title='Chemical Engineering',target_field='Chemical Engineering',target_countries='[]',funding_requirement='MEDIUM')
 process=opportunity_view(p,chem_goal,opp('Process Lab','RESEARCH',['Process Engineering'],['EXPERIENCE']),[gap],{'overall':20});assert process['field_relevance']==100

def test_economics_personalization_integration_and_isolation():
 h=auth_setup('economics-personalization@example.com')
 profile={'birth_year':date.today().year-17,'country':'Kazakhstan','city':'','education_level':'HIGH_SCHOOL','grade_year':'12','gpa':3.9,'gpa_scale':4,'english_level':'B2','ielts_score':None,'sat_score':None,'budget_level':'LOW','preferred_countries':['Europe'],'preferred_fields':['Economics'],'skills':[],'interests':['Economics'],'achievements':'none','projects':'none','extracurriculars':'none','volunteering':'none','research_experience':'none','work_experience':'none'}
 goal={'title':'Economics in Europe','description':'Study Economics bachelor in Europe with substantial funding','goal_type':'UNIVERSITY_ADMISSION','target_field':'Economics','target_countries':['Europe'],'funding_requirement':'HIGH','education_level':'BACHELOR','language':'English'}
 result=client.post('/api/onboarding/complete',headers=h,json={'profile':profile,'goal':goal});assert result.status_code==200
 with SessionLocal() as db:
  for title,typ,fields,cats,restrict in [('Economics Olympiad','COMPETITION',['Economics'],['EXPERIENCE'],False),('Open Global Scholarship','SCHOLARSHIP',['General'],['FINANCIAL'],False),('Chemistry-specific Degree','UNIVERSITY_PROGRAM',['Chemistry'],['ACADEMIC'],True)]:
   db.add(Opportunity(title=title,provider='Test Demo Dataset',opportunity_type=typ,description='Demo dataset record',country='International',eligible_countries='["International"]',education_levels='["HIGH_SCHOOL"]',fields=json.dumps(fields),gap_categories=json.dumps(cats),field_restriction=restrict,funding_type='FULL',deadline=date.today()+timedelta(days=90),source_label='Demo dataset'))
  db.commit()
 stored=client.get('/api/profile',headers=h).json();assert stored['projects']=='none' and stored['research_experience']=='none' and stored['volunteering']=='none' and stored['extracurriculars']=='none' and stored['ielts_score'] is None and stored['preferred_fields']==['Economics'] and stored['preferred_countries']==['Europe']
 dash=client.get('/api/dashboard',headers=h).json();assert dash['goal']['target_field']=='Economics' and 'Chemical Engineering' not in dash['goal']['title'] and dash['readiness']['experience']<=20
 language=next(g for g in dash['gaps'] if g['category']=='LANGUAGE');assert 'exact target depends' in language['target_state'] and '6.5' not in language['target_state']
 feed=client.get('/api/opportunities',headers=h).json();titles=[o['title'] for o in feed];assert titles.index('Economics Olympiad')<titles.index('Open Global Scholarship') and 'Chemistry-specific Degree' not in titles
 advice=client.post('/api/ai/advisor',headers=h,json={'question':'find economics olympiads'}).json();assert advice['intent']=='OPPORTUNITY_SEARCH' and 'Economics Olympiad' in advice['answer'] and 'highest-severity gap' not in advice['answer']
 with SessionLocal() as db:
  user=db.query(User).filter_by(email='economics-personalization@example.com').one();assert db.query(Goal).filter_by(user_id=user.id).count()==1 and db.query(StudentProfile).filter_by(user_id=user.id).one().achievements=='none'

def economics_user(email='economics-search@example.com'):
 h=auth_setup(email)
 profile={'birth_year':date.today().year-19,'country':'Kazakhstan','city':'','education_level':'BACHELOR','grade_year':'1','gpa':3.8,'gpa_scale':4,'english_level':'B2','ielts_score':None,'sat_score':None,'budget_level':'MEDIUM','preferred_countries':['International'],'preferred_fields':['Economics'],'skills':[],'interests':['Economics'],'achievements':'','projects':'','extracurriculars':'','volunteering':'','research_experience':'','work_experience':''}
 goal={'title':'Economics Abroad','target_field':'Economics','target_countries':['International'],'funding_requirement':'MEDIUM','education_level':'BACHELOR','language':'English'}
 assert client.post('/api/onboarding/complete',headers=h,json={'profile':profile,'goal':goal}).status_code==200
 return h

def test_economics_search_aliases_and_recommendation_safety():
 from app.seed import seed
 seed();h=economics_user()
 economics=client.get('/api/opportunities',headers=h,params={'search':'economics'}).json()
 economy=client.get('/api/opportunities',headers=h,params={'search':'economy'}).json()
 assert len(economics)>=7 and {o['id'] for o in economics}=={o['id'] for o in economy}
 assert all(o['eligibility_status']=='ELIGIBLE' for o in economics)
 feed=client.get('/api/opportunities',headers=h).json()
 econ_positions=[i for i,o in enumerate(feed) if 'Economics' in o['title']]
 chemistry_positions=[i for i,o in enumerate(feed) if 'Chemistry' in o['title']]
 assert econ_positions and (not chemistry_positions or min(econ_positions)<min(chemistry_positions))
 assert not any(o['title']=='European Chemical Engineering BSc' for o in feed)

def test_seed_updates_existing_database_without_deleting_users():
 from app.seed import seed,ECONOMICS_OPPORTUNITIES
 h=auth_setup('persistent-user@example.com')
 with SessionLocal() as db:
  existing=db.query(Opportunity).filter_by(title=ECONOMICS_OPPORTUNITIES[0][0],source_label='Demo dataset').first()
  if existing:db.delete(existing)
  users=db.query(User).count();db.commit()
 seed()
 with SessionLocal() as db:
  assert db.query(User).count()>=users  # seed may add the demo account, never removes existing users
  assert db.query(User).filter_by(email='persistent-user@example.com').one()
  assert db.query(Opportunity).filter_by(title=ECONOMICS_OPPORTUNITIES[0][0],source_label='Demo dataset').one()

def test_advisor_returns_stored_economics_and_rejects_invented_record(monkeypatch):
 from app.main import ai
 from app.seed import seed
 seed();h=economics_user('advisor-economics@example.com')
 real_complete=ai.complete
 try:
  monkeypatch.setattr(ai,'complete',lambda _:json.dumps({'answer':'Apply to Invented Nobel Economics Camp by Friday.','recommendations':[{'id':999999,'reason':'Guaranteed admission'}],'general_suggestions':['join a school economics club']}))
  response=client.post('/api/ai/advisor',headers=h,json={'question':'find some economics extracurriculars'}).json()
 finally:monkeypatch.setattr(ai,'complete',real_complete)
 assert 'Student Economics Society Project' in response['answer']
 assert 'Invented Nobel Economics Camp' not in response['answer']
 assert 'General suggestions (not stored Pathly opportunities)' in response['answer']

def test_ai_provider_selection_and_real_call(monkeypatch):
 from app.config.settings import settings
 from app.services.ai import ResilientAIProvider
 monkeypatch.setattr(settings,'ai_provider','mock');monkeypatch.setattr(settings,'ai_api_key','')
 mock=ResilientAIProvider();assert mock.fallback_active and mock.complete('anything')
 monkeypatch.setattr(settings,'ai_provider','openai');monkeypatch.setattr(settings,'ai_api_key','server-secret')
 monkeypatch.setattr(settings,'ai_model','test-model');monkeypatch.setattr(settings,'ai_base_url','https://provider.test/v1')
 called={}
 class Response:
  def raise_for_status(self):pass
  def json(self):return {'choices':[{'message':{'content':'{"answer":"real","recommendations":[],"general_suggestions":[]}'}}]}
 def post(url,**kwargs):called.update(url=url,**kwargs);return Response()
 monkeypatch.setattr('app.services.ai.httpx.post',post)
 real=ResilientAIProvider();assert not real.fallback_active
 assert json.loads(real.complete('ADVISOR_JSON {}'))['answer']=='real'
 assert called['headers']['Authorization']=='Bearer server-secret' and called['json']['model']=='test-model'
 assert not real.fallback_active

def test_advisor_context_is_authenticated_user(monkeypatch):
 from app.main import ai
 h=economics_user('context-owner@example.com');captured={}
 def complete(prompt):
  captured.update(json.loads(prompt.split('ADVISOR_JSON ',1)[1]));return json.dumps({'answer':'ok','recommendations':[],'general_suggestions':[]})
 monkeypatch.setattr(ai,'complete',complete)
 client.post('/api/ai/advisor',headers=h,json={'question':'Why is my experience readiness 0?'})
 assert captured['context']['user']['name']=='Test User'
 assert captured['context']['goal']['field']=='Economics'
 assert captured['context']['readiness']['experience']==0
 assert captured['context']['readiness']['extracurricular']==0
 assert captured['context']['user']['name']!='Aruzhan Demo'
