import json
from abc import ABC, abstractmethod

import httpx

from ..config.settings import settings
from .domains import canonical_domain, detect_opportunity_type


class AIProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str: ...


class MockAIProvider(AIProvider):
    def complete(self, prompt: str) -> str:
        if 'PARSE_GOAL' in prompt:
            lower = prompt.lower()
            field = canonical_domain(lower.replace('parse_goal', ''))
            countries = [name for name in ['United States', 'Germany', 'Netherlands', 'United Kingdom', 'Canada', 'Europe', 'Asia'] if name.lower() in lower or (name == 'United States' and ' usa' in lower)]
            typ = detect_opportunity_type(lower)
            level = 'MASTER' if 'master' in lower else 'PHD' if 'phd' in lower or 'doctor' in lower else 'BACHELOR'
            return json.dumps({'goal_type': 'UNIVERSITY_ADMISSION', 'target_field': field, 'target_opportunity_type': typ, 'target_regions': countries, 'language': 'English', 'funding_requirement': 'HIGH' if any(x in lower for x in ('scholar', 'full funding', 'financial aid', 'substantial funding')) else 'MEDIUM', 'education_level': level, 'constraints': [], 'confidence': .91})
        if 'REVIEW' in prompt:
            return json.dumps({'overall_score': 72, 'requirement_coverage': {'Leadership': 70, 'Academic motivation': 88, 'Community impact': 35}, 'strengths': ['Clear academic motivation'], 'gaps': ['Community impact lacks concrete evidence'], 'recommendations': ['Add a concrete community-impact example and measurable outcome if one exists.']})
        if 'ADVISOR_JSON ' in prompt:
            payload = json.loads(prompt.split('ADVISOR_JSON ', 1)[1])
            ctx, opportunities = payload['context'], payload['candidate_opportunities']
            gap = ctx['open_gaps'][0] if ctx['open_gaps'] else None
            answer = f"For your {ctx['goal']['field']} goal, your readiness is {ctx['readiness']['overall']}%. "
            answer += f"Your first priority is {gap['title']} ({gap['category'].lower()})." if gap else 'Your known gaps are resolved; focus on completing your roadmap.'
            return json.dumps({'answer': answer, 'recommendations': [{'id': o['id'], 'reason': f"This can help with {', '.join(o['gap_categories']).lower() or 'your active goal'}."} for o in opportunities[:3]], 'general_suggestions': []})
        return 'Review your active path and choose the next incomplete roadmap task.'


class RealAIProvider(AIProvider):
    def complete(self, prompt: str) -> str:
        structured = any(marker in prompt for marker in ('PARSE_GOAL', 'REVIEW', 'ADVISOR_JSON'))
        body = {'model': settings.ai_model, 'messages': [{'role': 'user', 'content': prompt}]}
        if structured:
            body['response_format'] = {'type': 'json_object'}
        response = httpx.post(settings.ai_base_url.rstrip('/') + '/chat/completions', headers={'Authorization': f'Bearer {settings.ai_api_key}'}, json=body, timeout=20)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        if not isinstance(content, str) or not content.strip():
            raise ValueError('AI provider returned an empty response')
        if structured:
            parsed = json.loads(content)
            if 'ADVISOR_JSON' in prompt and not isinstance(parsed.get('recommendations'), list):
                raise ValueError('AI provider returned an invalid advisor response')
        return content


class ResilientAIProvider(AIProvider):
    def __init__(self):
        self.real = RealAIProvider()
        self.mock = MockAIProvider()
        self.configured_real = settings.ai_provider.strip().lower() not in ('', 'mock') and bool(settings.ai_api_key.strip())
        self.last_fallback = not self.configured_real

    @property
    def fallback_active(self):
        return self.last_fallback

    @property
    def provider_name(self):
        return 'mock' if self.fallback_active else settings.ai_provider

    def complete(self, prompt: str) -> str:
        if not self.configured_real:
            self.last_fallback = True
            return self.mock.complete(prompt)
        for _ in range(2):
            try:
                result = self.real.complete(prompt)
                self.last_fallback = False
                return result
            except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                continue
        self.last_fallback = True
        return self.mock.complete(prompt)


ai = ResilientAIProvider()
