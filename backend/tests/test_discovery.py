import pytest
import json
from app.database import Base,engine,SessionLocal
from app.models import Opportunity
from app.services.discovery import RawSearchResult,RejectionReason,ResultCategory,classify,discover,persist_candidates,qualify
from app.services.domains import canonical_domain,requested_domains

def setup_function():
 Base.metadata.drop_all(engine);Base.metadata.create_all(engine)

def test_deterministic_unsafe_source_classification_and_rejection():
 cases=[
  (RawSearchResult('Math Olympiads discussion','https://reddit.com/r/math/x','competition'),ResultCategory.FORUM),
  (RawSearchResult('Math competitions','https://facebook.com/post/1','olympiad'),ResultCategory.SOCIAL_MEDIA),
  (RawSearchResult('Top 10 Best Math Competitions','https://example.com/top-math','ranked list'),ResultCategory.DIRECTORY_OR_LISTICLE),
  (RawSearchResult('How to enter math competitions','https://example.com/advice','tips'),ResultCategory.GENERAL_INFORMATION),
  (RawSearchResult('Math competition news','https://medium.com/story','article'),ResultCategory.NEWS_OR_BLOG),
 ]
 for result,category in cases:
  assert classify(result)==category
  assert qualify(result,'find math olympiads')[0] is None
 with SessionLocal() as db:
  admitted,rejected=persist_candidates(db,[x[0] for x in cases],'find math olympiads')
  assert not admitted and len(rejected)==len(cases) and db.query(Opportunity).count()==0

def test_official_concrete_result_admitted_without_invented_facts():
 raw=RawSearchResult('International Mathematical Olympiad | Official Site','https://www.imo-official.org/','The mathematics olympiad competition for students')
 with SessionLocal() as db:
  admitted,rejected=persist_candidates(db,[raw],'find math olympiads')
  assert not rejected and len(admitted)==1
  opp=admitted[0]
  assert opp.source_label=='Source Found' and opp.source_domain=='imo-official.org'
  assert opp.funding_type=='UNKNOWN' and opp.funding_amount_text is None and opp.deadline is None
  assert opp.verified_at is None and opp.is_first_party and opp.official_url=='https://www.imo-official.org/'

def test_duplicate_official_representations_collapse():
 raw=[RawSearchResult('International Mathematical Olympiad | Official Site','https://imo-official.org/','Official mathematics olympiad competition'),RawSearchResult('International Mathematical Olympiad | IMO','https://imo-official.org/?ref=search','Official mathematics olympiad competition')]
 with SessionLocal() as db:
  admitted,rejected=persist_candidates(db,raw,'math olympiads')
  assert len(admitted)==1 and len(rejected)==1 and rejected[0]['reason']=='DUPLICATE'
  assert db.query(Opportunity).count()==1

class Provider:
 def __init__(self,results=None,error=None):self.results=results or [];self.error=error
 def search(self,query):
  if self.error:raise self.error
  return self.results

def test_provider_failure_is_explicit_and_successful_zero_does_not_fallback():
 with SessionLocal() as db:
  failed=discover(db,'physics olympiads',Provider(error=TimeoutError()))
  assert failed['mode']=='DEMO' and failed['fallback_used'] and failed['error']
  empty=discover(db,'physics olympiads',Provider([RawSearchResult('Physics discussion','https://reddit.com/r/physics','olympiad')]))
  assert empty['mode']=='EXTERNAL' and not empty['fallback_used'] and empty['raw_result_count']==1 and empty['rejected_count']==1 and not empty['admitted']
  assert db.query(Opportunity).count()==0

def test_subject_aliases_and_types_are_strict_and_generalize():
 assert requested_domains('find physics olympiads')==['Physics']
 assert requested_domains('economy competitions')==requested_domains('economics competitions')==['Economics']
 samples=[('chemistry olympiad','Chemistry'),('math olympiad','Mathematics'),('physics olympiad','Physics'),('economics competition','Economics'),('computer science competition','Computer Science'),('chemical engineering scholarship','Chemical Engineering')]
 for words,domain in samples:
  result=RawSearchResult(f'Official {words.title()}','https://institution.edu/apply',f'Applications for the {words} are open')
  data,_=qualify(result,'find '+words)
  assert data and json.loads(data['fields'])==[domain]
 assert canonical_domain('physics')=='Physics'

def test_problem_bank_is_not_admitted_as_opportunity():
    result = RawSearchResult(
        "Chemistry Olympiad Past Papers and Problem Archive",
        "https://chemistry-resources.example/problems",
        "Chemistry olympiad past problems, solutions and practice materials.",
    )

    data, category = qualify(result, "find chemistry olympiads")

    assert data is None
    assert category == RejectionReason.RESOURCE_PAGE


@pytest.mark.parametrize(("query", "result", "domain"), [
    ("chemistry olympiad", RawSearchResult("National Chemistry Olympiad", "https://science-foundation.org/chemistry-olympiad", "High school students can register to participate in this annual chemistry olympiad."), "Chemistry"),
    ("physics olympiad", RawSearchResult("National Physics Olympiad", "https://physicsolympiad.example/", "Registration is open to students for the annual physics olympiad."), "Physics"),
    ("economics competition", RawSearchResult("Young Economists Challenge", "https://economists.example/challenge", "Students are eligible to enter this economics competition."), "Economics"),
])
def test_subject_specific_actionable_opportunities_qualify(query, result, domain):
    data, reason = qualify(result, query)
    assert data is not None, reason
    assert json.loads(data["fields"]) == [domain]


def test_rejection_reasons_distinguish_non_opportunities_and_mismatches():
    cases = [
        (RawSearchResult("10 Best Chemistry Olympiads for Students", "https://publisher.example/list", "A ranked list of competitions"), "chemistry olympiad", RejectionReason.DIRECTORY_OR_LISTICLE),
        (RawSearchResult("Chemistry Olympiad discussion", "https://reddit.com/r/chemistry/1", "How can students enter?"), "chemistry olympiad", RejectionReason.FORUM),
        (RawSearchResult("Physics Olympiad", "https://physics.example/", "Students can register for this physics competition."), "chemistry olympiad", RejectionReason.SUBJECT_MISMATCH),
    ]
    for result, query, expected in cases:
        assert qualify(result, query) == (None, expected)


def test_canonical_duplicate_ignores_www_scheme_query_and_fragment():
    raw = [
        RawSearchResult("Chemistry Challenge", "http://www.chemchallenge.example/apply?utm_source=x", "Students can apply for this chemistry competition."),
        RawSearchResult("Annual Chemical Sciences Challenge", "https://chemchallenge.example/apply#registration", "Students can register for this chemistry competition."),
    ]
    with SessionLocal() as db:
        admitted, rejected = persist_candidates(db, raw, "chemistry competition")
        assert len(admitted) == 1
        assert [item["reason"] for item in rejected] == ["DUPLICATE"]
