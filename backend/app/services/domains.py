import re

# One maintained vocabulary is used by goal parsing, search, and recommendation scoring.
# Aliases are intentionally broader than the current demo records.
DOMAIN_ALIASES = {
    "Economics": {"economics", "economy", "economic", "economic policy", "econometrics"},
    "Finance": {"finance", "financial markets", "investment", "banking"},
    "Business": {"business", "entrepreneurship", "commerce", "management"},
    "Computer Science": {"computer science", "computing", "software", "programming", "cybersecurity"},
    "AI": {"artificial intelligence", "ai", "machine learning"},
    "Data Science": {"data science", "data analytics", "data analysis"},
    "Chemistry": {"chemistry", "green chemistry", "organic chemistry", "inorganic chemistry", "geochemistry"},
    "Physics": {"physics", "physical science", "astronomy", "astrophysics"},
    "Biology": {"biology", "biological science", "life science", "biochemistry", "bioinformatics"},
    "Geography": {"geography", "geographic", "human geography", "physical geography"},
    "Chemical Engineering": {"chemical engineering", "process engineering", "materials science", "biotechnology"},
    "Engineering": {"engineering", "mechanical engineering", "electrical engineering", "civil engineering", "environmental engineering", "energy engineering"},
    "Mathematics": {"mathematics", "math", "statistics", "mathematical modeling"},
    "Philosophy": {"philosophy", "ethics"},
    "Writing": {"writing", "essay", "literature", "creative writing"},
    "History": {"history", "historical studies"},
    "STEM": {"stem", "science technology engineering mathematics"},
    "Social Sciences": {"social science", "political science", "international relations", "public policy", "sociology"},
    "General": {"general", "all fields", "any field", "multidisciplinary", "international students"},
}

TYPE_ALIASES = {
    "COMPETITION": {"olympiad", "competition", "contest", "challenge", "hackathon", "essay prize", "writing prize", "student essay award"},
    "SCHOLARSHIP": {"scholarship", "studentship", "bursary", "financial aid", "tuition award"},
    "RESEARCH": {"research program", "research programme", "research experience", "research opportunity", "research placement", "summer research", "fellowship"},
    "SUMMER_SCHOOL": {"summer school", "summer program", "summer programme", "summer academy"},
    "INTERNSHIP": {"internship", "intern program", "intern programme", "work placement", "research internship"},
    "UNIVERSITY_PROGRAM": {"undergraduate program", "undergraduate programme", "undergraduate degree", "bachelor", "bsc", "degree program", "degree programme"},
    "VOLUNTEERING": {"volunteer", "volunteering", "community service"},
    "LANGUAGE_PROGRAM": {"language course", "language program", "language programme", "language school", "ielts preparation", "toefl preparation", "english preparation"},
    "COURSE": {"course", "training program", "training programme", "certificate program", "certificate programme"},
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
    # Prefer a named specialization over its parent token ("chemical engineering"
    # must not become two independent requested domains).
    if "Chemical Engineering" in found and "Engineering" in found:
        found.remove("Engineering")
    # Audience wording is represented by the General vocabulary for scoring,
    # but it is not a requested academic subject during discovery.
    if "General" in found:
        found.remove("General")
    return found

def domain_set(values) -> set[str]:
    return {canonical_domain(v) for v in values if v}

def field_relevance(goal_field: str, opportunity_fields: list[str]) -> int:
    goal = canonical_domain(goal_field)
    offered = domain_set(opportunity_fields)
    if not offered or "General" in offered:
        return 15 if goal != "General" else 100
    if goal in offered:
        return 100
    if {goal, *offered}.issuperset({"Chemistry", "Chemical Engineering"}):
        return 85
    # Adjacent commercial disciplines are relevant, but not direct field matches.
    commercial = {"Economics", "Finance", "Business"}
    if goal in commercial and offered.intersection(commercial):
        return 70
    # Adjacent STEM domains receive partial credit, never the score of a direct match.
    adjacent = {"Chemistry", "Physics", "Chemical Engineering", "Engineering", "Mathematics", "Computer Science", "AI", "Data Science"}
    if goal in adjacent and offered.intersection(adjacent):
        return 35
    return 5

def search_matches_domain(search: str, opportunity_fields: list[str]) -> bool:
    """Match a recognized search alias against structured opportunity metadata."""
    searched = canonical_domain(search)
    return searched in DOMAIN_ALIASES and field_relevance(searched, opportunity_fields) >= 70

def detect_opportunity_type(text: str) -> str | None:
    value = clean(text)
    # Prefer the most specific phrase. This keeps "research internship" an
    # internship and "summer research program" research, while preventing the
    # generic word "program" from turning department pages into degrees.
    matches = []
    for typ, aliases in TYPE_ALIASES.items():
        for alias in aliases:
            normalized = clean(alias)
            if re.search(rf"\b{re.escape(normalized)}s?\b", value):
                matches.append((len(normalized.split()), len(normalized), typ))
    if not matches:
        # Funding words are only meaningful together; a lone "award" or
        # "grant" is too ambiguous to identify a scholarship.
        if re.search(r"\b(award|grant|funding)\b", value) and re.search(
            r"\b(tuition|financial|student|scholar|study|education|applicants?|eligibility)\b", value
        ):
            return "SCHOLARSHIP"
        return None
    return max(matches)[2]
