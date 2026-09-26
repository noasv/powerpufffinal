import json
import os
import tempfile
from datetime import date, timedelta

import pytest

os.environ['DATABASE_URL'] = 'sqlite:///' + tempfile.mktemp(suffix='.db')

from app.config.settings import settings
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import Opportunity
from app.services.advisor_intent import EXTRACURRICULAR_TYPES, parse_advisor_opportunity_intent
from fastapi.testclient import TestClient


client = TestClient(app)


@pytest.mark.parametrize(("question", "is_search", "subject", "typ", "umbrella", "uses_goal"), [
    ("find some extracurriculars related to chemistry", True, "Chemistry", None, True, False),
    ("what extracurriculars should I do?", True, "Chemistry", None, True, True),
    ("find economics competitions", True, "Economics", "COMPETITION", False, False),
    ("find chemistry research opportunities", True, "Chemistry", "RESEARCH", False, False),
    ("find essay competitions about economics", True, "Economics", "COMPETITION", False, False),
    ("find scholarships for international students", True, None, "SCHOLARSHIP", False, False),
    ("find a chemical engineering bachelor program", True, "Chemical Engineering", "UNIVERSITY_PROGRAM", False, False),
    ("what is my readiness?", False, None, None, False, False),
    ("why is my readiness low?", False, None, None, False, False),
    ("explain my roadmap", False, None, None, False, False),
])
def test_advisor_opportunity_intent_examples(question, is_search, subject, typ, umbrella, uses_goal):
    intent = parse_advisor_opportunity_intent(question, "Chemistry")
    assert intent.is_discovery is is_search
    assert (intent.subjects[0] if intent.subjects else None) == subject
    assert intent.requested_type == typ
    assert intent.extracurricular is umbrella
    assert intent.used_active_goal is uses_goal
    if umbrella:
        assert intent.allowed_types == EXTRACURRICULAR_TYPES
        assert "student activities opportunities apply" in intent.discovery_query
        assert "scholarship" not in intent.discovery_query
    if question == "find economics competitions":
        assert intent.discovery_query == "Economics competition"


def _chemistry_user(email):
    token = client.post('/api/auth/register', json={
        'name': 'Chem Student', 'email': email, 'password': 'Password1!', 'country': 'Kazakhstan'
    }).json()['access_token']
    headers = {'Authorization': 'Bearer ' + token}
    profile = {
        'birth_year': date.today().year - 17, 'country': 'Kazakhstan',
        'education_level': 'HIGH_SCHOOL', 'grade_year': '11', 'gpa': 3.8,
        'gpa_scale': 4, 'english_level': 'B2', 'budget_level': 'LOW',
        'preferred_countries': [], 'preferred_fields': ['Chemistry'], 'skills': [],
        'interests': ['Chemistry'], 'achievements': '', 'projects': '',
        'extracurriculars': '', 'volunteering': '', 'research_experience': '',
        'work_experience': '', 'city': '', 'ielts_score': None, 'sat_score': None,
    }
    goal = {'title': 'Chemistry', 'target_field': 'Chemistry', 'target_countries': [],
            'funding_requirement': 'MEDIUM', 'education_level': 'BACHELOR', 'language': 'English'}
    assert client.post('/api/onboarding/complete', headers=headers,
                       json={'profile': profile, 'goal': goal}).status_code == 200
    return headers


def _opportunity(title, field, typ='COMPETITION', status='SOURCE_FOUND'):
    return Opportunity(
        title=title, provider='Test Provider', opportunity_type=typ,
        description=f'A source-backed {field} activity.', fields=json.dumps([field]),
        gap_categories='["EXPERIENCE"]', eligible_countries='["International"]',
        education_levels='["HIGH_SCHOOL"]', deadline=date.today() + timedelta(days=90),
        source_url=f'https://example.org/{title.lower().replace(" ", "-")}',
        source_label='Source Found', source_type='CONCRETE_OPPORTUNITY',
        verification_status=status,
    )


def test_advisor_uses_matching_stored_opportunity_before_external_search(monkeypatch):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    headers = _chemistry_user('stored-chemistry@example.com')
    with SessionLocal() as db:
        db.add_all([_opportunity('Chemistry Challenge', 'Chemistry'),
                    _opportunity('Economics Essay Prize', 'Economics')])
        db.commit()
    monkeypatch.setattr(settings, 'opportunity_discovery_provider', 'serper')
    monkeypatch.setattr('app.main.discover', lambda *_: pytest.fail('stored match must avoid external discovery'))

    data = client.post('/api/ai/advisor', headers=headers,
                       json={'question': 'find extracurriculars related to chemistry'}).json()
    assert data['intent'] == 'OPPORTUNITY_SEARCH'
    assert 'Chemistry Challenge' in data['answer']
    assert 'Economics Essay Prize' not in data['answer']
    assert [item['title'] for item in data['opportunities']] == ['Chemistry Challenge']
    assert 'source-backed: SOURCE_FOUND' in data['answer']


def test_advisor_external_fallback_exposes_only_persisted_admitted_records(monkeypatch):
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    headers = _chemistry_user('fallback-chemistry@example.com')
    calls = []

    def fake_discover(db, query):
        calls.append(query)
        admitted = _opportunity('Persisted Chemistry Lab', 'Chemistry', 'RESEARCH')
        db.add(admitted); db.commit(); db.refresh(admitted)
        # A raw/rejected name is represented only in metrics, never persisted.
        return {'mode': 'EXTERNAL', 'fallback_used': False, 'error': None,
                'raw_result_count': 2, 'rejected_count': 1, 'admitted': [admitted],
                'rejected': [{'title': 'Rejected Raw Candidate'}]}

    monkeypatch.setattr(settings, 'opportunity_discovery_provider', 'serper')
    monkeypatch.setattr('app.main.discover', fake_discover)
    data = client.post('/api/ai/advisor', headers=headers,
                       json={'question': 'find some extracurriculars related to chemistry'}).json()

    assert calls == ['Chemistry student activities opportunities apply']
    assert 'Persisted Chemistry Lab' in data['answer']
    assert 'Rejected Raw Candidate' not in data['answer']
    assert data['discovery']['admitted_count'] == 1
    assert data['discovery']['rejected_count'] == 1
