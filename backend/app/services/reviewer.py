import re
from typing import Literal

from pydantic import BaseModel, Field, model_validator


ReviewStatus = Literal['COMPLETE', 'INSUFFICIENT_CONTENT']
CriterionStatus = Literal['SUPPORTED', 'PARTIAL', 'MISSING', 'NOT_APPLICABLE']


class ReviewCriterion(BaseModel):
    criterion: str
    score: int = Field(ge=0, le=100)
    status: CriterionStatus
    evidence: list[str]
    reason: str
    recommendation: str

    @model_validator(mode='after')
    def missing_has_no_credit(self):
        if self.status in ('MISSING', 'NOT_APPLICABLE') and self.score != 0:
            raise ValueError('missing or non-applicable criteria cannot receive credit')
        if self.status == 'MISSING' and self.evidence:
            raise ValueError('missing criteria cannot contain evidence')
        return self


class ApplicationReview(BaseModel):
    review_status: ReviewStatus
    overall_score: float | None = Field(default=None, ge=0, le=100)
    summary: str
    criteria: list[ReviewCriterion]
    strengths: list[str]
    missing_evidence: list[str]
    recommendations: list[str]

    @model_validator(mode='after')
    def insufficient_has_no_score(self):
        if self.review_status == 'INSUFFICIENT_CONTENT' and self.overall_score is not None:
            raise ValueError('insufficient submissions must not show a polished overall score')
        return self


TYPE_RUBRICS = {
    'COMPETITION': [
        ('Subject preparation', ('chemistry', 'subject', 'coursework', 'studied', 'study', 'grade')),
        ('Relevant achievements', ('placed', 'won', 'award', 'medal', 'ranked', 'olympiad', 'competition')),
        ('Competition experience', ('olympiad', 'competition', 'tournament', 'contest')),
        ('Motivation and readiness', ('because', 'want', 'goal', 'prepare', 'motivat', 'ready')),
        ('Concrete evidence', ('project', 'research', 'result', 'completed', 'built', 'led', 'improved')),
    ],
    'RESEARCH': [
        ('Subject knowledge', ('chemistry', 'science', 'coursework', 'studied', 'grade')),
        ('Research interest', ('research', 'investigat', 'question', 'experiment')),
        ('Relevant experience', ('project', 'research', 'lab', 'experiment', 'completed')),
        ('Technical preparation', ('method', 'analysis', 'data', 'software', 'laboratory')),
        ('Motivation', ('because', 'want', 'goal', 'motivat')),
    ],
    'SCHOLARSHIP': [
        ('Academic strength', ('grade', 'gpa', 'academic', 'coursework', 'placed', 'award')),
        ('Motivation', ('because', 'want', 'goal', 'motivat')),
        ('Requirement coverage', ('eligible', 'requirement', 'financial', 'income', 'country')),
        ('Leadership', ('led', 'leader', 'organized', 'founded', 'captain')),
        ('Community impact', ('volunteer', 'community', 'mentored', 'outreach', 'service')),
    ],
    'UNIVERSITY_PROGRAM': [
        ('Academic fit', ('grade', 'gpa', 'coursework', 'studied', 'academic')),
        ('Motivation', ('because', 'want', 'goal', 'motivat')),
        ('Requirement coverage', ('requirement', 'language', 'ielts', 'eligible')),
        ('Relevant experience', ('project', 'research', 'work', 'intern')),
        ('Application completeness', ('because', 'experience', 'goal', 'contribute')),
    ],
}


def rubric_for(opportunity_type: str, requirements: str):
    rubric = list(TYPE_RUBRICS.get(opportunity_type, TYPE_RUBRICS['UNIVERSITY_PROGRAM']))
    req = requirements.lower()
    optional = {'Leadership': ('leadership', 'leader'), 'Community impact': ('community', 'volunteer'), 'Financial context': ('financial', 'income', 'funding')}
    existing = {name for name, _ in rubric}
    for name, words in optional.items():
        if name not in existing and any(word in req for word in words):
            rubric.append((name, words))
    return rubric


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r'(?<=[.!?])\s+|\n+', text.strip()) if part.strip()]


def deterministic_review(opportunity_type: str, requirements: str, content: str) -> ApplicationReview:
    sentences = _sentences(content)
    lower = content.lower()
    word_count = len(re.findall(r"\b[\w'-]+\b", content))
    concrete = bool(re.search(r'\b\d+(?:\.\d+)?%?\b', content)) or any(word in lower for word in ('placed', 'won', 'completed', 'project', 'research', 'led', 'built', 'improved'))
    meaningful = word_count >= 20 and len(sentences) >= 2 and concrete
    criteria = []
    for name, keywords in rubric_for(opportunity_type, requirements):
        matching = [sentence for sentence in sentences if any(keyword in sentence.lower() for keyword in keywords)]
        if not matching:
            criteria.append(ReviewCriterion(criterion=name, score=0, status='MISSING', evidence=[], reason='No supporting evidence was found in this draft.', recommendation=f'Add truthful, specific evidence for {name.lower()} if you have it.'))
            continue
        quote = matching[0]
        detailed = concrete and (bool(re.search(r'\d', quote)) or any(word in quote.lower() for word in ('placed', 'won', 'completed', 'project', 'research', 'led', 'built', 'improved')))
        status = 'SUPPORTED' if detailed else 'PARTIAL'
        score = 80 if detailed else 25
        criteria.append(ReviewCriterion(criterion=name, score=score, status=status, evidence=[quote], reason='The draft provides concrete supporting evidence.' if detailed else 'The draft makes a relevant claim but does not substantiate it with a concrete example or result.', recommendation='Keep this evidence and explain its relevance to this specific opportunity.' if detailed else 'Add a concrete example, achievement, result, coursework, or project if one exists.'))
    applicable = [criterion.score for criterion in criteria if criterion.status != 'NOT_APPLICABLE']
    overall = round(sum(applicable) / len(applicable), 1) if meaningful and applicable else None
    missing = [criterion.criterion for criterion in criteria if criterion.status == 'MISSING']
    strengths = [criterion.criterion for criterion in criteria if criterion.status == 'SUPPORTED']
    recommendations = [criterion.recommendation for criterion in criteria if criterion.status in ('MISSING', 'PARTIAL')]
    return ApplicationReview(
        review_status='COMPLETE' if meaningful else 'INSUFFICIENT_CONTENT',
        overall_score=overall,
        summary='Evidence-based review completed against the stored opportunity requirements.' if meaningful else 'Insufficient content for a meaningful application review.',
        criteria=criteria,
        strengths=strengths,
        missing_evidence=missing,
        recommendations=list(dict.fromkeys(recommendations)),
    )


def validate_provider_review(raw: str, content: str, allowed_criteria: set[str]) -> ApplicationReview:
    review = ApplicationReview.model_validate_json(raw)
    normalized = content.casefold()
    for criterion in review.criteria:
        if criterion.criterion not in allowed_criteria:
            raise ValueError('provider introduced an unknown criterion')
        if criterion.status in ('SUPPORTED', 'PARTIAL') and not criterion.evidence:
            raise ValueError('positive score lacks evidence')
        for quote in criterion.evidence:
            if quote.strip().casefold() not in normalized:
                raise ValueError('provider evidence is not present in the submitted document')
    applicable = [criterion.score for criterion in review.criteria if criterion.status != 'NOT_APPLICABLE']
    expected = round(sum(applicable) / len(applicable), 1) if applicable else None
    if review.review_status == 'COMPLETE' and review.overall_score != expected:
        review.overall_score = expected
    return review
