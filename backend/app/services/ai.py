import json,httpx
from abc import ABC,abstractmethod
from ..config.settings import settings
class AIProvider(ABC):
 @abstractmethod
 def complete(self,prompt:str)->str: ...
class MockAIProvider(AIProvider):
 def complete(self,prompt):
  if 'PARSE_GOAL' in prompt:return json.dumps({'goal_type':'UNIVERSITY_ADMISSION','target_field':'Chemical Engineering' if 'chemical' in prompt.lower() else 'Engineering','target_regions':['Europe'],'language':'English','funding_requirement':'HIGH' if 'scholar' in prompt.lower() else 'MEDIUM','education_level':'BACHELOR','confidence':.91})
  if 'REVIEW' in prompt:return json.dumps({'overall_score':72,'requirement_coverage':{'Leadership':70,'Academic motivation':88,'Community impact':35},'strengths':['Clear academic motivation'],'gaps':['Community impact lacks concrete evidence'],'recommendations':['Add a concrete community-impact example and measurable outcome if one exists.']})
  return 'Focus on your highest-severity open gap. Based on your path, complete one concrete task this week and verify opportunity facts at the official source.'
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
