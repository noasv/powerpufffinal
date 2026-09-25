import json
import logging
from abc import ABC, abstractmethod

import httpx

from ..config.settings import settings
from .domains import canonical_domain, detect_opportunity_type

logger = logging.getLogger(__name__)


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
            from .reviewer import deterministic_review
            payload = json.loads(prompt.split('REVIEW_JSON ', 1)[1])
            return deterministic_review(payload['opportunity_type'], payload['requirements'], payload['content']).model_dump_json()
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
        response = httpx.post(settings.ai_base_url.rstrip('/') + '/chat/completions', headers={'Authorization': f'Bearer {settings.ai_api_key}'}, json=body, timeout=settings.ai_timeout_seconds)
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
        self.last_fallback = False
        self.last_active_provider = 'mock' if not self.configured_real else settings.ai_provider

    @property
    def fallback_active(self):
        return self.last_active_provider == 'mock'

    @property
    def provider_name(self):
        return self.last_active_provider

    @property
    def configured_provider(self):
        return settings.ai_provider if self.configured_real else 'mock'

    def complete(self, prompt: str) -> str:
        if not self.configured_real:
            self.last_fallback = False
            self.last_active_provider = 'mock'
            logger.info('AI request completed provider=mock fallback_used=false')
            return self.mock.complete(prompt)
        for _ in range(2):
            try:
                result = self.real.complete(prompt)
                self.last_fallback = False
                self.last_active_provider = settings.ai_provider
                logger.info('AI request completed provider=%s fallback_used=false', settings.ai_provider)
                return result
            except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                logger.warning('AI provider failed provider=%s error=%s', settings.ai_provider, type(exc).__name__)
                continue
        self.last_fallback = True
        self.last_active_provider = 'mock'
        logger.warning('AI request completed provider=mock fallback_used=true')
        return self.mock.complete(prompt)


ai = ResilientAIProvider()
