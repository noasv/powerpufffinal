"""External opportunity discovery with a hard qualification boundary.

Search engine records are leads, never Opportunity objects.  This module only
admits a result when deterministic evidence indicates that the result itself is
a concrete program page on a source suitable to show users.
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from collections import Counter
import json,re
import logging
from urllib.parse import urlsplit,urlunsplit
import httpx
from sqlalchemy.orm import Session
from ..config.settings import settings
from ..models import Opportunity
from .domains import DOMAIN_ALIASES,clean,detect_opportunity_type,requested_domains

class ResultCategory(str,Enum):
 CONCRETE_OPPORTUNITY="CONCRETE_OPPORTUNITY";OFFICIAL_OPPORTUNITY_PAGE="OFFICIAL_OPPORTUNITY_PAGE";DIRECTORY_OR_LISTICLE="DIRECTORY_OR_LISTICLE";NEWS_OR_BLOG="NEWS_OR_BLOG";SOCIAL_MEDIA="SOCIAL_MEDIA";FORUM="FORUM";SEARCH_AGGREGATOR="SEARCH_AGGREGATOR";GENERAL_INFORMATION="GENERAL_INFORMATION";UNKNOWN="UNKNOWN"

class RejectionReason(str,Enum):
 SOCIAL_MEDIA="SOCIAL_MEDIA";FORUM="FORUM";DIRECTORY_OR_LISTICLE="DIRECTORY_OR_LISTICLE";NEWS_OR_BLOG="NEWS_OR_BLOG";SEARCH_AGGREGATOR="SEARCH_AGGREGATOR";GENERAL_INFORMATION="GENERAL_INFORMATION";RESOURCE_PAGE="RESOURCE_PAGE";SUBJECT_MISMATCH="SUBJECT_MISMATCH";TYPE_MISMATCH="TYPE_MISMATCH";NO_PARTICIPATION_SIGNAL="NO_PARTICIPATION_SIGNAL";NOT_CONCRETE_OPPORTUNITY="NOT_CONCRETE_OPPORTUNITY";INVALID_URL="INVALID_URL";DUPLICATE="DUPLICATE"

@dataclass(frozen=True)
class RawSearchResult:
 title:str; url:str; snippet:str=""

SOCIAL={"facebook.com","instagram.com","linkedin.com","tiktok.com","x.com","twitter.com","youtube.com"}
FORUMS={"reddit.com","quora.com","stackexchange.com"}
AGGREGATORS={"google.com","bing.com","search.yahoo.com"}
BLOG_HOSTS={"medium.com","substack.com","blogspot.com","wordpress.com"}
LISTICLE=re.compile(r"\b(top|best)\s+\d+\b|\b\d+\s+(best\s+)?(olympiads?|competitions?|scholarships?|opportunities)\b|\blist of\b",re.I)
ADVICE=re.compile(r"\b(how to|guide to|tips for|what is|why (join|enter)|rankings?|roundup|resources? for)\b",re.I)
NEWS=re.compile(r"\b(news|blog|article|announces?|winners?|results?|recap)\b",re.I)
CONCRETE=re.compile(r"\b(olympiad|competition|challenge|scholarship|fellowship|internship|summer school|research program|exchange program|award|grant|bursary)\b",re.I)

# Search results can mention a real competition while actually pointing to a
# problem bank, archive, study resource, or informational page. These pages
# are useful resources, but they are not actionable Opportunity records.
RESOURCE_ONLY=re.compile(
 r"\b(problem bank|problem archive|past problems?|practice problems?|"
 r"practice questions?|solutions? archive|study materials?|learning resources?|"
 r"collection of .* problems?|explore [\d,]+\+? .*problems?)\b",
 re.I,
)
PARTICIPATION=re.compile(
 r"\b(register|registration|apply|application|participate|participant|"
 r"eligibility|eligible|enroll|enrollment|enter|students? compete|"
 r"competitors?|open to|deadline|submission|submit|join)\b",
 re.I,
)
logger=logging.getLogger(__name__)

def domain_of(url:str)->str:
 try:return urlsplit(url).hostname.lower().removeprefix("www.")
 except (AttributeError,ValueError):return ""
def _in(domain:str,blocked:set[str])->bool:return any(domain==x or domain.endswith("."+x) for x in blocked)
def canonicalize_url(url:str)->str:
 try:
  p=urlsplit(url.strip());
  if p.scheme not in {"http","https"} or not p.hostname:return ""
  host=p.hostname.lower().removeprefix("www.")
  port=f":{p.port}" if p.port and not (p.scheme.lower()=="http" and p.port==80) and not (p.scheme.lower()=="https" and p.port==443) else ""
  return urlunsplit((p.scheme.lower(),host+port,p.path.rstrip("/") or "/","",""))
 except ValueError:return ""

def classify(result:RawSearchResult)->ResultCategory:
 domain=domain_of(result.url); text=f"{result.title} {result.snippet}"; path=urlsplit(result.url).path.lower()
 if not canonicalize_url(result.url):return ResultCategory.UNKNOWN
 if _in(domain,SOCIAL):return ResultCategory.SOCIAL_MEDIA
 if _in(domain,FORUMS) or "forum" in domain:return ResultCategory.FORUM
 if _in(domain,AGGREGATORS):return ResultCategory.SEARCH_AGGREGATOR
 if LISTICLE.search(text):return ResultCategory.DIRECTORY_OR_LISTICLE
 if _in(domain,BLOG_HOSTS) or NEWS.search(result.title) or re.search(r"/(blog|news|articles?|posts?)/",path):return ResultCategory.NEWS_OR_BLOG
 if ADVICE.search(result.title):return ResultCategory.GENERAL_INFORMATION
 if not CONCRETE.search(text):return ResultCategory.GENERAL_INFORMATION
 # Institution, government, and organizer pages are strong first-party signals.
 if domain.endswith((".edu",".ac.uk",".gov")) or re.search(r"\b(official|apply|application|registration)\b",text,re.I):return ResultCategory.OFFICIAL_OPPORTUNITY_PAGE
 # A dedicated organizer domain normally shares a meaningful brand word with
 # the program title. Arbitrary publishers do not get this trust signal.
 brand={x for x in re.split(r"[^a-z0-9]+",domain.split('.')[0]) if len(x)>3}
 title_words=set(clean(result.title).split())
 return ResultCategory.CONCRETE_OPPORTUNITY if brand & title_words else ResultCategory.UNKNOWN

def _detected_domains(text:str)->list[str]:
 normalized=clean(text)
 return [name for name,aliases in DOMAIN_ALIASES.items() if any(re.search(rf"\b{re.escape(clean(alias))}\b",normalized) for alias in aliases)]

def _reason_for_category(category:ResultCategory)->RejectionReason:
 try:return RejectionReason(category.value)
 except ValueError:return RejectionReason.NOT_CONCRETE_OPPORTUNITY

def _url_identity(url:str)->tuple[str,str]:
 parts=urlsplit(url)
 return domain_of(url),(parts.path.rstrip('/') or '/').lower()

def _title(raw:str)->str:
 # Remove only obvious browser-title branding; never manufacture a program name.
 return re.split(r"\s+[|–—]\s+",raw.strip(),maxsplit=1)[0].strip()
def _provider(raw:RawSearchResult)->str:
 branded=re.split(r"\s+[|–—]\s+",raw.title.strip(),maxsplit=1)
 return branded[1].strip() if len(branded)>1 else domain_of(raw.url)
def qualify(result:RawSearchResult,query:str):
 category=classify(result)
 evidence=f"{result.title} {result.snippet}"
 if not canonicalize_url(result.url):return None,RejectionReason.INVALID_URL
 if RESOURCE_ONLY.search(evidence):return None,RejectionReason.RESOURCE_PAGE
 # Search snippets for first-party homepages often use an organization's name
 # as the title. Strong, explicit participation language is enough to identify
 # a concrete opportunity even when that name does not resemble its domain.
 if category==ResultCategory.UNKNOWN and CONCRETE.search(evidence) and PARTICIPATION.search(evidence):
  category=ResultCategory.CONCRETE_OPPORTUNITY
 if category not in {ResultCategory.CONCRETE_OPPORTUNITY,ResultCategory.OFFICIAL_OPPORTUNITY_PAGE}:return None,_reason_for_category(category)
 query_type=detect_opportunity_type(query);typ=detect_opportunity_type(evidence)
 domains=requested_domains(query)
 if not typ or (query_type and typ!=query_type):return None,RejectionReason.TYPE_MISMATCH
 if not domains:return None,RejectionReason.SUBJECT_MISMATCH
 # Explicit query intent is strict: the result must contain the requested subject
 # in its visible search evidence, rather than inheriting it by assumption.
 result_domains=_detected_domains(evidence)
 if not any(d in result_domains for d in domains):return None,RejectionReason.SUBJECT_MISMATCH

 # A search hit about an opportunity is not necessarily an opportunity itself.
 # Reject obvious archives/problem banks unless the visible evidence also
 # contains a concrete participation signal.
 if category==ResultCategory.CONCRETE_OPPORTUNITY and not PARTICIPATION.search(evidence):
  # Dedicated domains whose brand occurs in the title are credible organizer
  # pages; all other non-institutional results need an actionable signal.
  brand={x for x in re.split(r"[^a-z0-9]+",domain_of(result.url).split('.')[0]) if len(x)>3}
  if not brand.intersection(clean(result.title).split()):return None,RejectionReason.NO_PARTICIPATION_SIGNAL

 url=canonicalize_url(result.url); domain=domain_of(url); first=category==ResultCategory.OFFICIAL_OPPORTUNITY_PAGE
 return {'title':_title(result.title),'provider':_provider(result),'opportunity_type':typ,'description':result.snippet.strip() or 'Source page found; details have not yet been extracted.','official_url':url,'country':'Unknown','delivery_mode':'UNKNOWN','eligible_countries':'[]','education_levels':'[]','fields':json.dumps(domains),'field_restriction':True,'funding_type':'UNKNOWN','funding_amount_text':None,'cost_text':None,'language_requirements':None,'deadline':None,'requirements_text':'','source_label':'Source Found','gap_categories':'[]','source_url':url,'source_type':category.value,'source_domain':domain,'verification_status':'SOURCE_FOUND','discovered_at':datetime.utcnow(),'canonical_source_url':url,'discovery_source_url':url,'source_quality':'FIRST_PARTY' if first else 'CREDIBLE_SOURCE','is_first_party':first,'verification_notes':'Search evidence identifies a concrete opportunity; structured facts remain unverified.','last_checked_at':datetime.utcnow()},category

class SerperProvider:
 def search(self,query:str)->list[RawSearchResult]:
  response=httpx.post(settings.opportunity_search_base_url,headers={'X-API-KEY':settings.opportunity_search_api_key,'Content-Type':'application/json'},json={'q':query,'num':10},timeout=settings.opportunity_search_timeout_seconds)
  response.raise_for_status(); payload=response.json()
  if not isinstance(payload,dict) or not isinstance(payload.get('organic',[]),list):raise ValueError('Malformed discovery response')
  return [RawSearchResult(str(x.get('title','')),str(x.get('link','')),str(x.get('snippet',''))) for x in payload['organic'] if isinstance(x,dict)]

def persist_candidates(db:Session,raw:list[RawSearchResult],query:str):
 admitted=[];rejected=[];seen=set()
 for lead in raw:
  data,category=qualify(lead,query)
  if not data:rejected.append({'title':lead.title,'reason':category.value});continue
  key=(clean(data['title']),data['source_domain'])
  url_key=_url_identity(data['canonical_source_url'])
  if url_key in seen or key in seen:rejected.append({'title':lead.title,'reason':RejectionReason.DUPLICATE.value});continue
  seen.update((url_key,key))
  existing=db.query(Opportunity).filter((Opportunity.canonical_source_url==data['canonical_source_url']) | ((Opportunity.title==data['title']) & (Opportunity.source_domain==data['source_domain']))).first()
  if not existing:
   existing=next((candidate for candidate in db.query(Opportunity).filter_by(source_domain=data['source_domain']).all() if _url_identity(candidate.canonical_source_url or candidate.official_url)==url_key),None)
  if existing:
   admitted.append(existing);continue
  opp=Opportunity(**data);db.add(opp);db.flush();admitted.append(opp)
 db.commit();return admitted,rejected

def discover(db:Session,query:str,provider=None):
 configured=settings.opportunity_discovery_provider.lower()
 if provider is None:
  if configured!='serper' or not settings.opportunity_search_api_key:return {'mode':'DEMO','fallback_used':True,'error':'External discovery is not configured.','raw_result_count':0,'rejected_count':0,'admitted':[]}
  provider=SerperProvider()
 try:raw=provider.search(query)
 except Exception as exc:
  return {'mode':'DEMO','fallback_used':True,'error':f'External provider unavailable: {type(exc).__name__}','raw_result_count':0,'rejected_count':0,'admitted':[]}
 admitted,rejected=persist_candidates(db,raw,query)
 reasons=dict(Counter(item['reason'] for item in rejected))
 logger.info('Discovery summary query=%r raw=%d rejected=%d admitted=%d reasons=%s',query,len(raw),len(rejected),len(admitted),reasons)
 for item in rejected:logger.debug('Discovery rejection query=%r title=%r reason=%s',query,item['title'],item['reason'])
 return {'mode':'EXTERNAL','fallback_used':False,'error':None,'raw_result_count':len(raw),'rejected_count':len(rejected),'admitted':admitted,'rejection_summary':reasons}
