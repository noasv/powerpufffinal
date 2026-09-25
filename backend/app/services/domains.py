import re

# One maintained vocabulary is used by goal parsing, search, and recommendation scoring.
# Aliases are intentionally broader than the current demo records.
DOMAIN_ALIASES = {
    "Economics": {"economics", "economy", "economic", "economic policy", "econometrics"},
    "Finance": {"finance", "financial markets", "investment", "banking"},
    "Business": {"business", "entrepreneurship", "commerce", "management"},
    "Computer Science": {"computer science", "computing", "software", "programming", "artificial intelligence", "ai", "machine learning", "data science", "cybersecurity"},
    "Chemistry": {"chemistry", "green chemistry", "organic chemistry", "inorganic chemistry", "geochemistry"},
    "Geography": {"geography", "geographic", "human geography", "physical geography"},
    "Chemical Engineering": {"chemical engineering", "process engineering", "materials science", "biotechnology"},
    "Engineering": {"engineering", "mechanical engineering", "electrical engineering", "civil engineering", "environmental engineering", "energy engineering"},
    "Mathematics": {"mathematics", "math", "statistics", "mathematical modeling"},
    "Social Sciences": {"social science", "political science", "international relations", "public policy", "sociology"},
    "General": {"general", "all fields", "any field", "multidisciplinary", "international students"},
}

TYPE_ALIASES = {
    "COMPETITION": {"olympiad", "olympiads", "competition", "challenge", "case competition"},
    "RESEARCH": {"research", "lab", "fellowship"},
    "SCHOLARSHIP": {"scholarship", "funding", "grant", "financial aid"},
    "UNIVERSITY_PROGRAM": {"degree", "bachelor", "masters", "university", "program"},
    "INTERNSHIP": {"internship", "work placement"},
    "VOLUNTEERING": {"volunteer", "volunteering", "community service"},
    "LANGUAGE_PROGRAM": {"language course", "ielts", "toefl", "english preparation"},
    "COURSE": {"course", "training"},
}

def clean(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()

def canonical_domain(value: str) -> str:
    value = clean(value)
    if not value:
        return "General"
    matches = [(name, max((len(clean(a)) for a in aliases if clean(a) in value), default=0)) for name, aliases in DOMAIN_ALIASES.items()]
    name, length = max(matches, key=lambda item: item[1])
    return name if length else value.title()

def requested_domains(value: str) -> list[str]:
    """Return every explicit domain in a query, including slash-separated domains."""
    normalized = clean(value)
    found = []
    for name, aliases in DOMAIN_ALIASES.items():
        if any(re.search(rf"\b{re.escape(clean(alias))}\b", normalized) for alias in aliases):
            found.append(name)
    return found

def domain_set(values) -> set[str]:
    return {canonical_domain(v) for v in values if v}

def field_relevance(goal_field: str, opportunity_fields: list[str]) -> int:
    goal = canonical_domain(goal_field)
    offered = domain_set(opportunity_fields)
    if not offered or "General" in offered:
        return 75
    if goal in offered:
        return 100
    if {goal, *offered}.issuperset({"Chemistry", "Chemical Engineering"}):
        return 85
    # Adjacent commercial disciplines are relevant, but not direct field matches.
    commercial = {"Economics", "Finance", "Business"}
    if goal in commercial and offered.intersection(commercial):
        return 70
    # Adjacent STEM domains receive partial credit, never the score of a direct match.
    adjacent = {"Chemistry", "Chemical Engineering", "Engineering", "Mathematics", "Computer Science"}
    if goal in adjacent and offered.intersection(adjacent):
        return 35
    return 5

def search_matches_domain(search: str, opportunity_fields: list[str]) -> bool:
    """Match a recognized search alias against structured opportunity metadata."""
    searched = canonical_domain(search)
    return searched in DOMAIN_ALIASES and field_relevance(searched, opportunity_fields) >= 70

def detect_opportunity_type(text: str) -> str | None:
    value = clean(text)
    for typ, aliases in TYPE_ALIASES.items():
        if any(clean(alias) in value for alias in aliases):
            return typ
    return None
