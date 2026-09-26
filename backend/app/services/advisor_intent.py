"""Deterministic interpretation of opportunity requests made to the Advisor.

This module translates student language into filters and a concise discovery
query.  It does not decide whether a search result is an opportunity; that
security boundary remains in ``services.discovery``.
"""
from dataclasses import dataclass
import re

from .domains import clean, detect_opportunity_type, requested_domains


EXTRACURRICULAR_TYPES = frozenset({
    "COMPETITION", "RESEARCH", "SUMMER_SCHOOL", "INTERNSHIP",
    "VOLUNTEERING", "COURSE", "LANGUAGE_PROGRAM", "EXCHANGE",
})

_OPPORTUNITY_NOUNS = re.compile(
    r"\b(opportunit(?:y|ies)|extracurriculars?|activities|outside school|competitions?|"
    r"olympiads?|contests?|research|scholarships?|bursaries|internships?|"
    r"volunteering|courses?|program(?:s|mes)?|bachelors?|degrees?)\b"
)
_DISCOVERY_ACTIONS = re.compile(
    r"\b(find|search|recommend|suggest|show|participate|join|apply|do outside school)\b"
)
_DISCOVERY_QUESTIONS = re.compile(
    r"\b(what|which|any|are there|do i have)\b.*\b(opportunit(?:y|ies)|"
    r"extracurriculars?|activities|program(?:s|mes)?|competitions?)\b"
)

_QUERY_TYPE = {
    "COMPETITION": "competition",
    "RESEARCH": "research program",
    "SUMMER_SCHOOL": "summer program",
    "INTERNSHIP": "internship",
    "VOLUNTEERING": "volunteer program",
    "COURSE": "course",
    "LANGUAGE_PROGRAM": "language program",
    "SCHOLARSHIP": "scholarship",
    "UNIVERSITY_PROGRAM": "bachelor program",
}


@dataclass(frozen=True)
class AdvisorOpportunityIntent:
    is_discovery: bool
    subjects: tuple[str, ...] = ()
    requested_type: str | None = None
    extracurricular: bool = False
    allowed_types: frozenset[str] | None = None
    discovery_query: str | None = None
    used_active_goal: bool = False


def parse_advisor_opportunity_intent(question: str, active_goal_field: str = "") -> AdvisorOpportunityIntent:
    """Parse Advisor language without asking the LLM to invent search intent."""
    value = clean(question)
    explicit_subjects = tuple(requested_domains(value))
    requested_type = detect_opportunity_type(value)
    if requested_type is None and re.search(r"\bresearch\b", value):
        requested_type = "RESEARCH"
    if requested_type == "COMPETITION" and "essay" in value and len(explicit_subjects) > 1:
        # Here "essay" describes the competition format, not a second subject.
        explicit_subjects = tuple(x for x in explicit_subjects if x != "Writing")
    multiple_activity_types = bool(
        re.search(r"\b(competitions?|contests?|olympiads?)\b", value)
        and re.search(r"\bresearch\b", value)
    )
    if multiple_activity_types:
        requested_type = None
    extracurricular = bool(re.search(r"\b(extracurriculars?|activities|outside school)\b", value))
    is_discovery = bool(
        _OPPORTUNITY_NOUNS.search(value)
        and (_DISCOVERY_ACTIONS.search(value) or _DISCOVERY_QUESTIONS.search(value))
    )
    # Natural shorthand such as "find me something related to chemistry" has
    # no opportunity noun, but its discovery action + explicit subject does.
    if explicit_subjects and re.search(r"\b(find|search|recommend|suggest|show)\b", value):
        is_discovery = True
    if re.search(r"\b(what|which)\b.*\bparticipate\b", value):
        is_discovery = True
    if not is_discovery:
        return AdvisorOpportunityIntent(False)

    # Funding is orthogonal to an academic field: "scholarships for
    # international students" must stay an audience/funding request rather
    # than silently becoming a Chemistry scholarship request.
    use_goal_default = requested_type != "SCHOLARSHIP"
    used_active_goal = not explicit_subjects and bool(active_goal_field) and use_goal_default
    subjects = explicit_subjects or ((active_goal_field,) if used_active_goal else ())
    allowed_types = (frozenset({"COMPETITION", "RESEARCH"}) if multiple_activity_types
                     else EXTRACURRICULAR_TYPES if extracurricular and not requested_type else None)

    subject_text = " ".join(subjects)
    if allowed_types and not requested_type:
        # Deliberately avoid enumerating every internal type.  This produces one
        # broad provider request and lets the existing qualifier identify each
        # concrete result's actual type.
        parts = [subject_text, "student activities opportunities apply"]
    elif requested_type:
        parts = [subject_text, _QUERY_TYPE[requested_type]]
        if requested_type == "COMPETITION" and "essay" in value:
            parts.insert(1, "essay")
        if requested_type == "SCHOLARSHIP" and "international student" in value:
            parts.append("international students")
    else:
        parts = [subject_text, "student opportunities apply"]
    query = " ".join(part for part in parts if part).strip()
    return AdvisorOpportunityIntent(
        True, subjects, requested_type, extracurricular, allowed_types, query,
        used_active_goal,
    )
