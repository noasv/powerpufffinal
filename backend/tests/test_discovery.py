import pytest
import json
from app.database import Base,engine,SessionLocal
from app.models import Opportunity
from app.services.discovery import RawSearchResult,RejectionReason,ResultCategory,classify,discover,persist_candidates,qualify,search_query
from app.services.domains import canonical_domain,detect_opportunity_type,requested_domains

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


@pytest.mark.parametrize(("query", "result", "expected_type"), [
    ("chemistry olympiad", RawSearchResult("National Chemistry Olympiad", "https://chemistryolympiad.org/enter", "High school students may register for the chemistry olympiad; see eligibility and rules."), "COMPETITION"),
    ("essay competition", RawSearchResult("International Student Essay Prize", "https://essayprize.org/competition", "Enter the essay competition by the submission deadline; rules and prizes are available."), "COMPETITION"),
    ("scholarships for international students", RawSearchResult("International Excellence Award", "https://www.example.edu/scholarships/excellence", "Scholarship funding for international students: review eligibility and submit an application."), "SCHOLARSHIP"),
    ("undergraduate scholarships", RawSearchResult("National Student Scholarship", "https://education.gov.example/funding/student", "Government scholarship funding with application eligibility and deadline details."), "SCHOLARSHIP"),
    ("chemistry research program", RawSearchResult("Student Chemistry Research Experience", "https://research-foundation.org/program", "Apply for a mentored chemistry research program with laboratory projects."), "RESEARCH"),
    ("chemistry summer school", RawSearchResult("Chemistry Summer Academy", "https://summerchemistry.org/apply", "Students can apply to attend this chemistry summer school; program dates are listed."), "SUMMER_SCHOOL"),
    ("engineering internship", RawSearchResult("Student Engineering Internship", "https://engineers-foundation.org/internship", "Applications are open for student engineering intern positions and placements."), "INTERNSHIP"),
    ("chemical engineering bachelor", RawSearchResult("BSc Chemical Engineering", "https://www.example.edu/study/chemical-engineering", "Bachelor of Science degree curriculum, entry requirements, admissions and application."), "UNIVERSITY_PROGRAM"),
    ("STEM volunteering", RawSearchResult("Student STEM Volunteer Program", "https://stemvolunteers.org/join", "Join this STEM volunteer opportunity; participant registration is open."), "VOLUNTEERING"),
    ("programming course", RawSearchResult("Online Programming Course", "https://learning.example.org/programming", "Enroll in the student programming course and earn a certificate."), "COURSE"),
    ("English language program", RawSearchResult("English Language Programme", "https://languages.example.org/english", "Register and enroll in the English language program; applications are open."), "LANGUAGE_PROGRAM"),
])
def test_actionable_categories_qualify(query, result, expected_type):
    data, reason = qualify(result, query)
    assert data is not None, reason
    assert data["opportunity_type"] == expected_type


@pytest.mark.parametrize(("query", "result", "reason"), [
    ("essay competitions", RawSearchResult("How to win an essay competition", "https://writers.example/advice", "Essay-writing advice and tips for students."), RejectionReason.GENERAL_INFORMATION),
    ("essay competitions", RawSearchResult("Past Winning Essays Archive", "https://essayprize.org/archive", "Winning essays and sample essays from the student essay competition."), RejectionReason.RESOURCE_PAGE),
    ("scholarships", RawSearchResult("50 Best Scholarships for Students", "https://publisher.example/scholarships", "A list of scholarship opportunities."), RejectionReason.DIRECTORY_OR_LISTICLE),
    ("chemistry scholarships", RawSearchResult("History Student Scholarship", "https://www.example.edu/history/funding", "History students can apply for scholarship funding and tuition support."), RejectionReason.SUBJECT_MISMATCH),
    ("research programs", RawSearchResult("University Research News", "https://www.example.edu/news/research", "An article about scientific research projects and discoveries."), RejectionReason.NEWS_OR_BLOG),
    ("summer school", RawSearchResult("University Summer News", "https://www.example.edu/news/summer", "News article recapping events held by the university."), RejectionReason.NEWS_OR_BLOG),
    ("internships", RawSearchResult("Career advice for internships", "https://careers.example/advice", "Tips for finding an internship position and writing applications."), RejectionReason.GENERAL_INFORMATION),
    ("chemistry undergraduate program", RawSearchResult("Department of Chemistry", "https://www.example.edu/chemistry", "Faculty, research, news, and educational resources."), RejectionReason.GENERAL_INFORMATION),
    ("volunteering opportunities", RawSearchResult("Volunteer advice for students", "https://publisher.example/volunteer-advice", "A guide to finding community service."), RejectionReason.GENERAL_INFORMATION),
    ("chemistry course", RawSearchResult("Chemistry Learning Resources", "https://learn.example/resources", "Practice tests, solutions, and chemistry course materials."), RejectionReason.RESOURCE_PAGE),
    ("chemistry scholarships", RawSearchResult("Chemistry Olympiad", "https://chemistryolympiad.org/register", "Register for this chemistry olympiad competition."), RejectionReason.TYPE_MISMATCH),
])
def test_non_actionable_or_mismatched_results_are_rejected(query, result, reason):
    assert qualify(result, query) == (None, reason)


def test_broad_queries_do_not_invent_subject_or_unknown_facts():
    result = RawSearchResult(
        "International Excellence Scholarship",
        "https://www.example.edu/funding/excellence",
        "International students may apply; scholarship eligibility is available on the application page.",
    )
    data, reason = qualify(result, "scholarships for international students")
    assert data is not None, reason
    assert json.loads(data["fields"]) == []
    assert data["field_restriction"] is False
    assert data["deadline"] is data["funding_amount_text"] is data["language_requirements"] is None
    assert data["country"] == "Unknown"
    assert data["provider"] == ""
    assert json.loads(data["eligible_countries"]) == []


def test_type_detection_uses_specific_semantic_variants():
    cases = {
        "young writers contest": "COMPETITION",
        "student essay award application": "COMPETITION",
        "merit award tuition funding for applicants": "SCHOLARSHIP",
        "summer research experience": "RESEARCH",
        "international summer programme": "SUMMER_SCHOOL",
        "research internship": "INTERNSHIP",
        "Bachelor of Science degree": "UNIVERSITY_PROGRAM",
        "IELTS preparation programme": "LANGUAGE_PROGRAM",
    }
    for text, expected in cases.items():
        assert detect_opportunity_type(text) == expected
    assert detect_opportunity_type("university research news") is None
    assert requested_domains("scholarships for international students") == []


def test_search_query_keeps_intent_and_uses_one_actionable_hint():
    assert search_query("chemistry scholarship") == "chemistry scholarship official apply"
    assert search_query("essay competition official") == "essay competition official"
    assert search_query("chemistry news") == "chemistry news"
