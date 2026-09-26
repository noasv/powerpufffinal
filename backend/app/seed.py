import json
from datetime import date,timedelta
from .database import Base,engine,SessionLocal
from .models import *
from .services.engines import sync_gaps,readiness,generate_roadmap
from pwdlib import PasswordHash
TYPES=['SCHOLARSHIP']*10+['UNIVERSITY_PROGRAM']*8+['COMPETITION']*4+['RESEARCH']*5+['INTERNSHIP']*3+['VOLUNTEERING']*2+['COURSE']*3+['LANGUAGE_PROGRAM']*2+['SUMMER_SCHOOL']*2+['EXCHANGE']*2
NAMES=['Global Scholars Award','Future Engineers Scholarship','International Merit Grant','STEM Access Scholarship','Community Leaders Award','Women in Science Grant','Sustainable Futures Scholarship','Academic Excellence Fund','Global Citizens Grant','Innovation Scholarship','European Chemical Engineering BSc','Sustainable Process Engineering','International Engineering Bachelor','Applied Chemistry Program','Materials Science BSc','Environmental Engineering Degree','Biotechnology Bachelor','Energy Engineering Program','Young Innovators Challenge','Global Science Competition','Math Modeling Challenge','Sustainability Case Competition','Chemical Research Summer Lab','European Research Academy','Materials Discovery Summer School','Student Science Fellowship','Green Chemistry Lab Program','Engineering Virtual Internship','STEM Industry Internship','Social Impact Internship','Global Volunteer Network','Science Outreach Volunteers','Academic Writing Course','Data Skills for Scientists','Project Design Fundamentals','IELTS Preparation Path','English for University','Engineering Summer School','Science Leadership Summer School','European Student Exchange','Global STEM Exchange']
ECONOMICS_OPPORTUNITIES = [
 ('Youth Economics Policy Challenge','COMPETITION',['Economics'],['EXPERIENCE','EXTRACURRICULAR']),
 ('Economics and Finance Summer Institute','SUMMER_SCHOOL',['Economics','Finance'],['ACADEMIC','EXPERIENCE']),
 ('Economics Research Academy','RESEARCH',['Economics'],['EXPERIENCE']),
 ('Future Finance Case Competition','COMPETITION',['Finance','Business','Economics'],['EXPERIENCE','EXTRACURRICULAR']),
 ('Student Economics Society Project','VOLUNTEERING',['Economics'],['EXTRACURRICULAR']),
 ('Foundations of Economics Online Course','COURSE',['Economics'],['ACADEMIC']),
 ('Global Business Scholars Award','SCHOLARSHIP',['General','Economics','Business'],['FINANCIAL']),
]

def _opportunity_values(typ,fields,cats,index):
 return {'provider':'Pathly Demo Dataset','opportunity_type':typ,'description':f'A structured {typ.lower().replace("_"," ")} for motivated international students. This is a demo record, not a verified live listing.','official_url':'','source_url':'https://example.org/pathly-demo/'+str(index),'source_domain':'example.org','source_type':'DEMO','verification_status':'DEMO','discovered_at':None,'country':'International','delivery_mode':'ONLINE','min_age':16,'max_age':24,'eligible_countries':json.dumps(['International']),'education_levels':json.dumps(['HIGH_SCHOOL','BACHELOR']),'fields':json.dumps(fields),'field_restriction':typ=='UNIVERSITY_PROGRAM','funding_type':'FULL' if typ=='SCHOLARSHIP' else 'PARTIAL','funding_amount_text':'Demo funding; verify with source','language_requirements':'English B2','deadline':date.today()+timedelta(days=60+index*3),'start_date':date.today()+timedelta(days=100+index*3),'requirements_text':'Demo requirements: academic record, motivation statement, and relevant evidence. Verify before applying.','verified_at':None,'source_label':'Pathly Demo Dataset','gap_categories':json.dumps(cats)}

def upsert_canonical_opportunities(db):
 """Version the Demo catalogue in-place without deleting users or user data."""
 catalogue=[]
 for name,typ in zip(NAMES,TYPES):
  lower=name.lower()
  cats=['EXPERIENCE'] if typ in ('RESEARCH','INTERNSHIP','COMPETITION','SUMMER_SCHOOL') else ['LANGUAGE'] if typ in ('LANGUAGE_PROGRAM','COURSE') and ('english' in lower or 'ielts' in lower) else ['FINANCIAL'] if typ=='SCHOLARSHIP' else ['ACADEMIC']
  if 'math' in lower:fields=['Mathematics']
  elif any(x in lower for x in ('ai ','coding','data skills')):fields=['Computer Science']
  elif typ=='SCHOLARSHIP' or any(x in lower for x in ('volunteer','academic writing','english','ielts')):fields=['General']
  elif any(x in lower for x in ('chemical','chemistry','process','materials','biotechnology')):fields=['Chemical Engineering']
  else:fields=['Engineering']
  catalogue.append((name,typ,fields,cats))
 catalogue.extend(ECONOMICS_OPPORTUNITIES)
 for i,(name,typ,fields,cats) in enumerate(catalogue):
  # Title plus the explicit source label is the stable canonical key.
  opp=db.query(Opportunity).filter_by(title=name,provider='Pathly Demo Dataset').first()
  if not opp:opp=Opportunity(title=name,source_label='Pathly Demo Dataset');db.add(opp)
  for key,value in _opportunity_values(typ,fields,cats,i).items():setattr(opp,key,value)
 db.flush()

def seed():
 Base.metadata.create_all(engine);db=SessionLocal()
 try:
  u=db.query(User).filter_by(email='student@demo.com').first()
  if not u:u=User(name='Aruzhan Demo',email='student@demo.com',password_hash=PasswordHash.recommended().hash('Demo123!'),country='Kazakhstan');db.add(u);db.flush()
  u.name='Aruzhan Demo';u.country='Kazakhstan'
  p=db.query(StudentProfile).filter_by(user_id=u.id).first()
  if not p:p=StudentProfile(user_id=u.id);db.add(p);db.flush()
  canonical={'birth_year':date.today().year-16,'country':'Kazakhstan','city':'','education_level':'HIGH_SCHOOL','grade_year':'11','gpa':3.8,'gpa_scale':4,'english_level':'B2','ielts_score':None,'budget_level':'LOW','preferred_countries':json.dumps(['Germany','Netherlands','International']),'preferred_fields':json.dumps(['Chemical Engineering']),'skills':json.dumps(['Chemistry','Mathematics']),'interests':json.dumps(['Sustainability']),'achievements':'Strong chemistry grades.','projects':'School chemistry project.','volunteering':'One school volunteering activity.','extracurriculars':'Chemistry club.','research_experience':'','work_experience':''}
  for key,value in canonical.items():setattr(p,key,value)
  g=db.query(Goal).filter_by(user_id=u.id,status='ACTIVE').first()
  if not g:g=Goal(user_id=u.id,title='Chemical Engineering in Europe');db.add(g);db.flush()
  db.query(Goal).filter(Goal.user_id==u.id,Goal.id!=g.id,Goal.status=='ACTIVE').update({'status':'PAUSED'},synchronize_session=False)
  g.title='Chemical Engineering in Europe';g.description='Study Chemical Engineering in Europe in English with substantial financial support.';g.target_field='Chemical Engineering';g.target_countries=json.dumps(['Germany','Netherlands']);g.funding_requirement='HIGH';g.education_level='BACHELOR';g.language='English';g.target_date=date.today()+timedelta(days=365);g.status='ACTIVE'
  if not db.query(Requirement).filter_by(goal_id=g.id).first():
   for cat,n,t in [('ACADEMIC','Strong STEM grades','3.2 GPA'),('LANGUAGE','English certification','IELTS 6.5'),('EXPERIENCE','Research evidence','One project'),('APPLICATION','Motivation letter','Complete draft'),('FINANCIAL','Funding plan','Full or substantial funding')]:db.add(Requirement(goal_id=g.id,category=cat,name=n,description=f'Evidence required: {n}',target_value=t))
  upsert_canonical_opportunities(db)
  sync_gaps(db,u.id,g,p)
  if not db.query(ReadinessSnapshot).filter_by(user_id=u.id,goal_id=g.id).first():readiness(db,u.id,g,p)
  generate_roadmap(db,u,g);db.commit();print(f'Seed complete: {db.query(Opportunity).count()} opportunities, demo user {u.email}')
 finally:db.close()
if __name__=='__main__':seed()
