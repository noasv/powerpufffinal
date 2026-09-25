import json
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from ..models import *
from ..config.scoring import *
from .domains import field_relevance

ABSENCE = {'', 'none', 'none yet', 'no', 'n/a', 'na', 'not yet', 'nothing'}

def j(value):
    try: return json.loads(value or '[]')
    except (TypeError, json.JSONDecodeError): return []

def has_evidence(value):
    return bool(value and value.strip().lower().rstrip('.') not in ABSENCE)

def eligibility(profile, opp, goal=None):
    reasons=[]; age=date.today().year-profile.birth_year if profile.birth_year else None
    if opp.deadline and opp.deadline<date.today(): reasons.append('Application deadline has passed.')
    if opp.min_age and age is not None and age<opp.min_age: reasons.append(f'Program requires applicants to be at least {opp.min_age}. Current profile indicates age {age}.')
    if opp.max_age and age is not None and age>opp.max_age: reasons.append(f'Program maximum age is {opp.max_age}.')
    if j(opp.eligible_countries) and profile.country not in j(opp.eligible_countries) and 'International' not in j(opp.eligible_countries): reasons.append(f'Applicants from {profile.country} are not listed as eligible.')
    if j(opp.education_levels) and profile.education_level not in j(opp.education_levels): reasons.append(f'Requires education level: {", ".join(j(opp.education_levels))}.')
    if goal and opp.field_restriction and field_relevance(goal.target_field,j(opp.fields)) < 50: reasons.append(f'This opportunity is restricted to {", ".join(j(opp.fields))}.')
    return ('NOT_ELIGIBLE' if reasons else 'ELIGIBLE',reasons or ['Known hard requirements are satisfied.'])

def sync_gaps(db,user_id,goal,profile):
    english_guidance='Official English certification may be required; exact target depends on selected programs.'
    experience=[]
    if not has_evidence(profile.projects): experience.append('projects')
    if not has_evidence(profile.research_experience): experience.append('research')
    extracurricular=[]
    if not has_evidence(profile.extracurriculars): extracurricular.append('extracurriculars')
    if not has_evidence(profile.volunteering): extracurricular.append('volunteering')
    if not has_evidence(profile.achievements): extracurricular.append('achievements')
    specs=[
      ('LANGUAGE','Official English evidence missing','No official English test score',english_guidance,'No verified English certification is stored. A precise threshold is unknown for this broad goal.',not profile.ielts_score),
      ('EXPERIENCE','Subject-related experience is limited','Missing '+', '.join(experience) if experience else 'Project/research evidence stored','Relevant project or research evidence','Profile evidence was checked for projects and research.',bool(experience)),
      ('EXTRACURRICULAR','Extracurricular evidence is limited','Missing '+', '.join(extracurricular) if extracurricular else 'Extracurricular evidence stored','Relevant activities, service, or achievements','Profile evidence was checked for extracurriculars, volunteering, and achievements.',bool(extracurricular)),
      ('APPLICATION','Motivation letter not prepared','No stored draft','Completed tailored motivation letter','No application document has been prepared.',not db.query(ApplicationDocument).filter_by(user_id=user_id).first()),
      ('FINANCIAL','Substantial funding required',profile.budget_level,'Funding plan','Profile budget and goal indicate substantial aid is required.',goal.funding_requirement=='HIGH')]
    existing={g.category:g for g in db.query(ProfileGap).filter_by(user_id=user_id,goal_id=goal.id).all()}
    for cat,title,current,target,evidence,missing in specs:
        g=existing.get(cat)
        if not g: g=ProfileGap(user_id=user_id,goal_id=goal.id,category=cat,title=title,description=f'{title} for the active goal.',severity='HIGH' if cat in ('LANGUAGE','EXPERIENCE','FINANCIAL') else 'MEDIUM',current_state=current,target_state=target,evidence=evidence);db.add(g)
        g.current_state=current;g.target_state=target;g.evidence=evidence;g.status='OPEN' if missing else 'RESOLVED';g.resolved_at=None if missing else datetime.utcnow()
    db.flush()

def readiness(db,user_id,goal,profile,save=True):
    academic=round((profile.gpa/profile.gpa_scale)*100) if profile.gpa is not None and profile.gpa_scale else 0
    language=95 if (profile.ielts_score or 0)>=7 else 80 if (profile.ielts_score or 0)>=6 else 35 if profile.english_level in ('B2','C1','C2') else 20
    exp_signals=[has_evidence(profile.projects),has_evidence(profile.research_experience),has_evidence(profile.work_experience)]
    extra_signals=[has_evidence(profile.extracurriculars),has_evidence(profile.volunteering),has_evidence(profile.achievements)]
    vals={'academic':min(100,academic),'language':language,'experience':round(sum(exp_signals)/len(exp_signals)*100),'extracurricular':round(sum(extra_signals)/len(extra_signals)*100),'financial':30 if goal.funding_requirement=='HIGH' and profile.budget_level=='LOW' else 60 if goal.funding_requirement=='HIGH' else 85,'application':75 if db.query(ApplicationDocument).filter_by(user_id=user_id).first() else 15}
    overall=round(sum(vals[k]*READINESS_WEIGHTS[k] for k in vals),1); data={'overall':overall,**vals}
    if save: db.add(ReadinessSnapshot(user_id=user_id,goal_id=goal.id,overall_readiness=overall,academic_readiness=vals['academic'],language_readiness=vals['language'],experience_readiness=vals['experience'],extracurricular_readiness=vals['extracurricular'],financial_readiness=vals['financial'],application_readiness=vals['application']))
    return data

def opportunity_view(profile,goal,opp,gaps,ready):
    status,reasons=eligibility(profile,opp,goal); fields=j(opp.fields); targets=j(goal.target_countries); cats=set(j(opp.gap_categories)); open_gaps=[g for g in gaps if g.status!='RESOLVED']; open_cats={g.category for g in open_gaps}
    relevance=field_relevance(goal.target_field,fields)
    intersection=open_cats.intersection(cats)
    impact_score=min(100,sum({'HIGH':45,'MEDIUM':30,'LOW':15}.get(g.severity,20) for g in open_gaps if g.category in cats))
    parts={'goal':relevance,'field':relevance,'location':100 if opp.country in targets or opp.country=='International' else 45,'funding':100 if goal.funding_requirement=='HIGH' and opp.funding_type=='FULL' else 75 if opp.funding_type=='PARTIAL' else 35,'profile':0 if status=='NOT_ELIGIBLE' else 85,'gap':impact_score}
    score=round(sum(parts[k]*MATCH_WEIGHTS[k] for k in parts)); score=min(score,25) if status=='NOT_ELIGIBLE' else score
    impacts=[{'gap_id':g.id,'category':g.category,'title':g.title,'strength':'HIGH' if g.severity=='HIGH' and impact_score>=45 else 'MEDIUM','reason':f'{opp.title} provides {g.category.lower()} evidence relevant to this open gap.'} for g in open_gaps if g.category in cats]
    strength='HIGH' if impact_score>=70 or any(i['strength']=='HIGH' for i in impacts) else 'MEDIUM' if impact_score>=40 or impacts else 'LOW'
    explanation=(f'Direct {goal.target_field} alignment; helps close '+', '.join(sorted(intersection)).lower()+' gaps.') if relevance>=75 and impacts else (f'Field relevance is low for a {goal.target_field} goal.' if relevance<40 else 'Broad field eligibility; review the stored requirements and gap impact.')
    return {'id':opp.id,'title':opp.title,'provider':opp.provider,'opportunity_type':opp.opportunity_type,'description':opp.description,'country':opp.country,'delivery_mode':opp.delivery_mode,'funding_type':opp.funding_type,'funding_amount_text':opp.funding_amount_text,'deadline':opp.deadline,'official_url':opp.official_url,'source_label':opp.source_label,'verified_at':opp.verified_at,'requirements_text':opp.requirements_text,'match_score':score,'field_relevance':relevance,'readiness_score':ready['overall'],'eligibility_status':status,'eligibility_reasons':reasons,'gap_impact':strength,'gap_impact_score':impact_score,'impacts':impacts,'explanation':explanation}

def generate_roadmap(db,user,goal,opp=None):
    road=db.query(Roadmap).filter_by(user_id=user.id,goal_id=goal.id).first() or Roadmap(user_id=user.id,goal_id=goal.id,title=f'Path to {goal.title}')
    db.add(road);db.flush(); deadline=(opp.deadline if opp else goal.target_date) or date.today()+timedelta(days=90)
    items=[('Start preparation',0),('Collect required documents',-35),('Draft motivation letter',-28),('Request recommendation',-21),('Final application review',-7),('Submit application',0)]
    for title,offset in items:
        due=date.today() if title=='Start preparation' else deadline+timedelta(days=offset)
        if not db.query(RoadmapTask).filter_by(roadmap_id=road.id,opportunity_id=opp.id if opp else None,title=title).first(): db.add(RoadmapTask(roadmap_id=road.id,opportunity_id=opp.id if opp else None,title=title,description='Complete this evidence-based preparation step.',due_date=due,priority='HIGH' if 'Submit' in title else 'MEDIUM'))
    db.flush();return road
