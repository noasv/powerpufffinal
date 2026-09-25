import json
from datetime import date,datetime,timedelta
from sqlalchemy.orm import Session
from ..models import *
from ..config.scoring import *
def j(value):
 try:return json.loads(value or '[]')
 except:return []
def eligibility(profile,opp):
 reasons=[]; age=date.today().year-profile.birth_year if profile.birth_year else None
 if opp.deadline and opp.deadline<date.today(): reasons.append('Application deadline has passed.')
 if opp.min_age and age is not None and age<opp.min_age: reasons.append(f'Program requires applicants to be at least {opp.min_age}. Current profile indicates age {age}.')
 if opp.max_age and age is not None and age>opp.max_age: reasons.append(f'Program maximum age is {opp.max_age}.')
 if j(opp.eligible_countries) and profile.country not in j(opp.eligible_countries) and 'International' not in j(opp.eligible_countries): reasons.append(f'Applicants from {profile.country} are not listed as eligible.')
 if j(opp.education_levels) and profile.education_level not in j(opp.education_levels): reasons.append(f'Requires education level: {", ".join(j(opp.education_levels))}.')
 return ('NOT_ELIGIBLE' if reasons else 'ELIGIBLE',reasons or ['Known hard requirements are satisfied.'])
def sync_gaps(db,user_id,goal,profile):
 specs=[('LANGUAGE','Official English evidence missing','No official IELTS score','IELTS 6.5 equivalent','Profile contains no IELTS score while certified English is required.',not profile.ielts_score),('EXPERIENCE','Research experience is limited',profile.research_experience or 'None yet','Subject-related project or research','Profile contains no subject-related research evidence.',not bool(profile.research_experience.strip())),('APPLICATION','Motivation letter not prepared','No stored draft','Completed tailored motivation letter','No application document has been prepared.',not db.query(ApplicationDocument).filter_by(user_id=user_id).first()),('FINANCIAL','Substantial funding required',profile.budget_level,'Funding plan','Profile budget and goal indicate substantial aid is required.',goal.funding_requirement=='HIGH')]
 existing={g.category:g for g in db.query(ProfileGap).filter_by(user_id=user_id,goal_id=goal.id).all()}
 for cat,title,current,target,evidence,missing in specs:
  g=existing.get(cat)
  if not g: g=ProfileGap(user_id=user_id,goal_id=goal.id,category=cat,title=title,description=f'{title} for the active goal.',severity='HIGH' if cat in ('LANGUAGE','FINANCIAL') else 'MEDIUM',current_state=current,target_state=target,evidence=evidence);db.add(g)
  g.current_state=current;g.status='OPEN' if missing else 'RESOLVED';g.resolved_at=None if missing else datetime.utcnow()
 db.flush()
def readiness(db,user_id,goal,profile,save=True):
 vals={'academic':min(100,round((profile.gpa or 2.5)/(profile.gpa_scale or 4)*100)),'language':95 if (profile.ielts_score or 0)>=6.5 else (65 if profile.english_level in ('B2','C1','C2') else 40),'experience':80 if profile.research_experience.strip() else 35,'extracurricular':75 if profile.extracurriculars.strip() or profile.volunteering.strip() else 40,'financial':65 if goal.funding_requirement=='HIGH' else 85,'application':75 if db.query(ApplicationDocument).filter_by(user_id=user_id).first() else 25}
 overall=round(sum(vals[k]*READINESS_WEIGHTS[k] for k in vals),1); data={'overall':overall,**vals}
 if save:
  db.add(ReadinessSnapshot(user_id=user_id,goal_id=goal.id,overall_readiness=overall,academic_readiness=vals['academic'],language_readiness=vals['language'],experience_readiness=vals['experience'],extracurricular_readiness=vals['extracurricular'],financial_readiness=vals['financial'],application_readiness=vals['application']))
 return data
def opportunity_view(profile,goal,opp,gaps,ready):
 status,reasons=eligibility(profile,opp); fields=j(opp.fields); targets=j(goal.target_countries); cats=j(opp.gap_categories); open_cats={g.category for g in gaps if g.status!='RESOLVED'}
 parts={'goal':100 if goal.goal_type else 60,'field':100 if goal.target_field.lower() in ' '.join(fields).lower() else 45,'location':100 if opp.country in targets or opp.country=='International' else 55,'funding':100 if goal.funding_requirement=='HIGH' and opp.funding_type in ('FULL','PARTIAL') else 60,'profile':0 if status=='NOT_ELIGIBLE' else 85,'gap':100 if open_cats.intersection(cats) else 30}
 score=round(sum(parts[k]*MATCH_WEIGHTS[k] for k in parts)); impacts=[{'gap_id':g.id,'title':g.title,'strength':'HIGH' if g.category in cats else 'LOW','reason':f'{opp.title} builds evidence in {g.category.lower()}.'} for g in gaps if g.status!='RESOLVED' and g.category in cats]
 strength='HIGH' if impacts else 'LOW'
 return {'id':opp.id,'title':opp.title,'provider':opp.provider,'opportunity_type':opp.opportunity_type,'description':opp.description,'country':opp.country,'delivery_mode':opp.delivery_mode,'funding_type':opp.funding_type,'funding_amount_text':opp.funding_amount_text,'deadline':opp.deadline,'official_url':opp.official_url,'source_label':opp.source_label,'verified_at':opp.verified_at,'requirements_text':opp.requirements_text,'match_score':score,'readiness_score':ready['overall'],'eligibility_status':status,'eligibility_reasons':reasons,'gap_impact':strength,'impacts':impacts,'explanation':('Strong fit because it can help close '+', '.join(open_cats.intersection(cats)).lower()+' gaps while aligning with your goal.') if impacts else 'This opportunity aligns with parts of your goal; review requirements carefully.'}
def generate_roadmap(db,user,goal,opp=None):
 road=db.query(Roadmap).filter_by(user_id=user.id,goal_id=goal.id).first() or Roadmap(user_id=user.id,goal_id=goal.id,title=f'Path to {goal.title}')
 db.add(road);db.flush(); deadline=(opp.deadline if opp else goal.target_date) or date.today()+timedelta(days=90)
 items=[('Start preparation',0),('Collect required documents',-35),('Draft motivation letter',-28),('Request recommendation',-21),('Final application review',-7),('Submit application',0)]
 for title,offset in items:
  due=date.today() if title=='Start preparation' else deadline+timedelta(days=offset)
  if not db.query(RoadmapTask).filter_by(roadmap_id=road.id,opportunity_id=opp.id if opp else None,title=title).first(): db.add(RoadmapTask(roadmap_id=road.id,opportunity_id=opp.id if opp else None,title=title,description='Complete this evidence-based preparation step.',due_date=due,priority='HIGH' if 'Submit' in title else 'MEDIUM'))
 db.flush();return road
