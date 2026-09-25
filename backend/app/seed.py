import json
from datetime import date,timedelta
from .database import Base,engine,SessionLocal
from .models import *
from .services.engines import sync_gaps,readiness,generate_roadmap
from pwdlib import PasswordHash
TYPES=['SCHOLARSHIP']*10+['UNIVERSITY_PROGRAM']*8+['COMPETITION']*5+['RESEARCH']*5+['INTERNSHIP']*3+['VOLUNTEERING']*2+['COURSE']*3+['LANGUAGE_PROGRAM']*2+['SUMMER_SCHOOL']*2+['EXCHANGE']*2
NAMES=['Global Scholars Award','Future Engineers Scholarship','International Merit Grant','STEM Access Scholarship','Community Leaders Award','Women in Science Grant','Sustainable Futures Scholarship','Academic Excellence Fund','Global Citizens Grant','Innovation Scholarship','European Chemical Engineering BSc','Sustainable Process Engineering','International Engineering Bachelor','Applied Chemistry Program','Materials Science BSc','Environmental Engineering Degree','Biotechnology Bachelor','Energy Engineering Program','International Chemistry Olympiad Prep','Young Innovators Challenge','Global Science Competition','Math Modeling Challenge','Sustainability Case Competition','Chemical Research Summer Lab','European Research Academy','Materials Discovery Summer School','Student Science Fellowship','Green Chemistry Lab Program','Engineering Virtual Internship','STEM Industry Internship','Social Impact Internship','Global Volunteer Network','Science Outreach Volunteers','Academic Writing Course','Data Skills for Scientists','Project Design Fundamentals','IELTS Preparation Path','English for University','Engineering Summer School','Science Leadership Summer School','European Student Exchange','Global STEM Exchange']
def seed():
 Base.metadata.create_all(engine);db=SessionLocal()
 try:
  u=db.query(User).filter_by(email='student@demo.com').first()
  if not u:u=User(name='Aruzhan Demo',email='student@demo.com',password_hash=PasswordHash.recommended().hash('Demo123!'),country='Kazakhstan');db.add(u);db.flush()
  u.name='Aruzhan Demo';u.country='Kazakhstan'
  p=db.query(StudentProfile).filter_by(user_id=u.id).first()
  if not p:p=StudentProfile(user_id=u.id);db.add(p);db.flush()
  canonical={'birth_year':date.today().year-16,'country':'Kazakhstan','city':'','education_level':'HIGH_SCHOOL','grade_year':'11','gpa':3.8,'gpa_scale':4,'english_level':'B2','ielts_score':None,'budget_level':'LOW','preferred_countries':json.dumps(['Germany','Netherlands','International']),'preferred_fields':json.dumps(['Chemical Engineering']),'skills':json.dumps(['Chemistry','Mathematics']),'interests':json.dumps(['Sustainability']),'achievements':'Strong chemistry and mathematics grades; school chemistry project.','volunteering':'One school volunteering activity.','extracurriculars':'School chemistry project.','research_experience':'','work_experience':''}
  for key,value in canonical.items():setattr(p,key,value)
  g=db.query(Goal).filter_by(user_id=u.id,status='ACTIVE').first()
  if not g:g=Goal(user_id=u.id);db.add(g);db.flush()
  db.query(Goal).filter(Goal.user_id==u.id,Goal.id!=g.id,Goal.status=='ACTIVE').update({'status':'PAUSED'},synchronize_session=False)
  g.title='Chemical Engineering in Europe';g.description='Study Chemical Engineering in Europe in English with substantial financial support.';g.target_field='Chemical Engineering';g.target_countries=json.dumps(['Germany','Netherlands']);g.funding_requirement='HIGH';g.education_level='BACHELOR';g.language='English';g.target_date=date.today()+timedelta(days=365);g.status='ACTIVE'
  if not db.query(Requirement).filter_by(goal_id=g.id).first():
   for cat,n,t in [('ACADEMIC','Strong STEM grades','3.2 GPA'),('LANGUAGE','English certification','IELTS 6.5'),('EXPERIENCE','Research evidence','One project'),('APPLICATION','Motivation letter','Complete draft'),('FINANCIAL','Funding plan','Full or substantial funding')]:db.add(Requirement(goal_id=g.id,category=cat,name=n,description=f'Evidence required: {n}',target_value=t))
  if db.query(Opportunity).count()==0:
   for i,(name,typ) in enumerate(zip(NAMES,TYPES)):
    cats=['EXPERIENCE'] if typ in ('RESEARCH','INTERNSHIP','COMPETITION','SUMMER_SCHOOL') else ['LANGUAGE'] if typ in ('LANGUAGE_PROGRAM','COURSE') and 'English' in name or 'IELTS' in name else ['FINANCIAL'] if typ=='SCHOLARSHIP' else ['ACADEMIC']
    db.add(Opportunity(title=name,provider=f'Pathly Demo Partner {i+1}',opportunity_type=typ,description=f'A structured {typ.lower().replace("_"," ")} for motivated international students, included for reliable product demonstration.',official_url='https://example.org/pathly-demo',country='International' if i%3 else 'Germany',delivery_mode='ONLINE' if i%2 else 'IN_PERSON',min_age=16,max_age=24,eligible_countries=json.dumps(['International']),education_levels=json.dumps(['HIGH_SCHOOL','BACHELOR']),fields=json.dumps(['Chemical Engineering','Engineering','Science']),funding_type='FULL' if typ=='SCHOLARSHIP' else 'PARTIAL',funding_amount_text='Demo funding; verify with source',language_requirements='English B2',deadline=date.today()+timedelta(days=45+i*3),start_date=date.today()+timedelta(days=90+i*3),requirements_text='Academic record, motivation statement, and evidence relevant to the program.',verified_at=date.today(),gap_categories=json.dumps(cats)))
  sync_gaps(db,u.id,g,p)
  if not db.query(ReadinessSnapshot).filter_by(user_id=u.id,goal_id=g.id).first():readiness(db,u.id,g,p)
  generate_roadmap(db,u,g);db.commit();print(f'Seed complete: {db.query(Opportunity).count()} opportunities, demo user {u.email}')
 finally:db.close()
if __name__=='__main__':seed()
