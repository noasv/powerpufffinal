import json,httpx
from abc import ABC,abstractmethod
from ..config.settings import settings
class AIProvider(ABC):
 @abstractmethod
 def complete(self,prompt:str)->str: ...
class MockAIProvider(AIProvider):
 def complete(self,prompt):
  if 'PARSE_GOAL' in prompt:
   lower=prompt.lower();field='Computer Science' if 'computer science' in lower else ('Chemical Engineering' if 'chemical' in lower else 'Engineering')
   regions=['United States'] if 'united states' in lower or ' usa' in lower else ['Europe']
   return json.dumps({'goal_type':'UNIVERSITY_ADMISSION','target_field':field,'target_regions':regions,'language':'English','funding_requirement':'HIGH' if 'scholar' in lower or 'full funding' in lower else 'MEDIUM','education_level':'BACHELOR','confidence':.91})
  if 'REVIEW' in prompt:return json.dumps({'overall_score':72,'requirement_coverage':{'Leadership':70,'Academic motivation':88,'Community impact':35},'strengths':['Clear academic motivation'],'gaps':['Community impact lacks concrete evidence'],'recommendations':['Add a concrete community-impact example and measurable outcome if one exists.']})
  if 'ADVISOR_CONTEXT ' in prompt:
   raw=prompt.split('ADVISOR_CONTEXT ',1)[1].split(' QUESTION ',1)[0];ctx=json.loads(raw);gaps=ctx['open_gaps'];top=gaps[0] if gaps else None
   if top:
    reason=f"Your current {top['severity'].lower()}-severity gap is “{top['title']}” ({top['category'].lower()})."
   else:reason='Your currently known requirements are covered, so focus on execution and keeping evidence current.'
   task=ctx['todo_tasks'][0] if ctx['todo_tasks'] else 'review and update your profile evidence'
   opp=f" for {ctx['saved_opportunities'][0]}" if ctx['saved_opportunities'] else ''
   return f"For your {ctx['goal']['field']} goal, focus this month on {reason} Your next concrete step is “{task}”{opp}. Overall readiness is {ctx['readiness']['overall']}% (a preparedness heuristic, not admission probability)."
  return 'Review your active path and choose the next incomplete roadmap task.'
class RealAIProvider(AIProvider):
 def complete(self,prompt):
  r=httpx.post(settings.ai_base_url.rstrip('/')+'/chat/completions',headers={'Authorization':f'Bearer {settings.ai_api_key}'},json={'model':settings.ai_model,'messages':[{'role':'user','content':prompt}],'response_format':{'type':'json_object'} if 'PARSE_GOAL' in prompt or 'REVIEW' in prompt else None},timeout=20);r.raise_for_status();return r.json()['choices'][0]['message']['content']
class ResilientAIProvider(AIProvider):
 def __init__(self): self.real=RealAIProvider();self.mock=MockAIProvider();self.fallback_active=settings.ai_provider=='mock' or not settings.ai_api_key
 def complete(self,prompt):
  if self.fallback_active:return self.mock.complete(prompt)
  for _ in range(2):
   try:return self.real.complete(prompt)
   except (httpx.HTTPError,KeyError,ValueError):pass
  self.fallback_active=True;return self.mock.complete(prompt)
ai=ResilientAIProvider()
