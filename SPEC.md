# Pathly — Complete MVP Technical Specification

> Authoritative specification for Claude Code / Codex.
> Treat this file as the source of truth for product scope, architecture, functionality, testing and delivery.

# 1. MISSION

Build **Pathly**, a complete, functional, demo-ready AI-powered EdTech platform.

This is NOT:
- a mockup;
- a static frontend;
- a proof of concept;
- pseudo-code;
- a starter template;
- a partially implemented application.

The finished repository must contain:

- working frontend;
- working backend;
- persistent database;
- authentication;
- deterministic recommendation logic;
- AI integration;
- reliable Demo AI fallback;
- seed data;
- automated tests;
- documentation;
- deployment configuration.

Core product promise:

> The user chooses the destination. Pathly identifies the gaps between their current profile and that destination, finds educational opportunities that can close those gaps, and continuously recalculates the best path forward.

Core loop:

GOAL  
→ PROFILE  
→ REQUIREMENTS  
→ GAP ANALYSIS  
→ OPPORTUNITIES  
→ OPPORTUNITY-TO-GAP MATCHING  
→ READINESS  
→ ROADMAP  
→ ACTION  
→ PROGRESS  
→ RECALCULATION

Do not stop after generating files.

You must install dependencies, initialize the database, seed demo data, run backend tests, run frontend type checking and production build, start the actual application, verify frontend/backend integration, test the main demo flow, fix discovered errors, and rerun failed checks.

No TODO placeholders.

No fake buttons.

No fake charts.

No hardcoded dashboard values pretending to be calculated.

No "implement later" for core functionality.

---

# 2. PRODUCT PROBLEM

Educational opportunities exist everywhere:

- scholarships;
- universities;
- olympiads;
- competitions;
- research programs;
- internships;
- summer schools;
- exchange programs;
- courses;
- fellowships;
- volunteering;
- language programs.

However, access to information does not guarantee access to opportunity.

Students frequently:

- discover opportunities too late;
- do not know which opportunities actually match them;
- misunderstand eligibility requirements;
- do not know which skills or achievements they are missing;
- see a long-term goal but do not know what to do next;
- miss deadlines;
- search across many fragmented websites;
- lack access to counselors or mentors;
- do not know which intermediate opportunities could strengthen their profile.

Most platforms answer:

> What opportunities exist?

Pathly must answer:

> Given who you are, where you want to go, and what you currently lack, what opportunity should you pursue next, what gap will it close, and why?

---

# 3. CORE PRODUCT INNOVATION

Do NOT build another scholarship search engine.

Do NOT build another generic AI college counselor.

Do NOT build a simple recommendation feed.

The core innovation is:

# Opportunity-to-Gap Matching

The system must understand:

1. the user's destination;
2. the user's current profile;
3. the requirements of the destination;
4. the gaps between current and target state;
5. which real opportunities could reduce those gaps.

Example goal:

> Study Chemical Engineering in Europe in English with substantial financial support.

Example current profile:

- Grade 11;
- Kazakhstan;
- strong chemistry and mathematics;
- English B2;
- no IELTS;
- no research experience;
- some volunteering;
- limited budget.

Possible gaps:

LANGUAGE GAP  
→ official English evidence missing

EXPERIENCE GAP  
→ research/project experience limited

APPLICATION GAP  
→ motivation letter missing

FINANCIAL GAP  
→ substantial funding required

A research summer program must NOT merely show:

Match: 87%

It should also show:

Closes:

✓ Research Experience Gap — HIGH  
✓ Subject Exploration Gap — MEDIUM

The core feedback loop is:

GOAL  
↓  
GAPS  
↓  
OPPORTUNITIES  
↓  
ACTION  
↓  
PROFILE UPDATE  
↓  
GAPS RECALCULATED  
↓  
NEXT BEST OPPORTUNITY

---

# 4. PRODUCT METAPHOR

Pathly is a navigation system for educational development.

Destination = educational goal.

Current location = current student profile.

Road conditions = eligibility, deadlines, cost and requirements.

Route = personalized roadmap.

Waypoints = educational opportunities.

Missing requirements = gaps.

Progress = completed milestones.

Recalculation = dynamic readiness engine.

Conceptually:

# Google Maps for educational opportunities.

This is a product explanation, not a visual gimmick.

---

# 5. TARGET USERS

Primary MVP users are students approximately 14–22 years old:

- high-school students;
- university applicants;
- undergraduate students;
- scholarship applicants;
- olympiad/competition applicants;
- research-program applicants.

The architecture must NOT hardcode Kazakhstan or any single country.

---

# 6. REQUIRED MVP SYSTEMS

The MVP MUST implement:

1. Authentication
2. Student Profile
3. Goal Builder
4. Goal Intelligence Engine
5. Requirement Engine
6. Gap Engine
7. Interactive Path / Gap Map
8. Opportunity Database
9. Eligibility Engine
10. Opportunity Matching Engine
11. Opportunity-to-Gap Matching
12. Readiness Engine
13. Opportunity Detail Page
14. Dynamic Roadmap
15. Task Tracking
16. Progress / Recalculation Engine
17. AI Path Advisor
18. Application Document Reviewer
19. Dashboard
20. Demo Mode
21. Real AI provider integration
22. Seed Data
23. Search / Filtering / Sorting
24. Error / Loading / Empty states
25. Tests
26. README
27. Docker / Deployment configuration

All P0 functionality must genuinely work.

---

# 7. TECH STACK

Choose reliability and simplicity over unnecessary complexity.

## Frontend

Use:

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- TanStack Query
- React Hook Form
- Zod
- Recharts
- Lucide React

## Backend

Use:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- JWT authentication
- secure password hashing

## Database

Development/demo:

SQLite.

Architecture must allow PostgreSQL using DATABASE_URL without rewriting business logic.

## AI

Implement provider abstraction:

AIProvider

RealAIProvider

MockAIProvider

Business logic MUST NOT directly depend on one AI provider.

Never expose API keys to frontend code.

---

# 8. AI CONFIGURATION

Support at minimum:

```env
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=
AI_BASE_URL=
```

If:

AI_PROVIDER=mock

OR an API key is missing:

use MockAIProvider.

If RealAIProvider fails:

RealAIProvider  
→ controlled retry  
→ MockAIProvider fallback

The application MUST remain demonstrable if external AI is unavailable during judging.

Display a subtle message when fallback is active:

> Demo AI mode is active.

Do not break the user flow.

---

# 9. AI RESPONSIBILITIES

AI must NOT exist only as a chatbot.

Use AI where natural-language reasoning is useful.

AI responsibilities:

- parse natural-language goals;
- extract structured goal information;
- explain profile gaps;
- summarize stored opportunity requirements;
- explain why an opportunity matters;
- generate natural-language roadmap explanations;
- analyze application documents;
- answer contextual questions about the user's path.

Deterministic backend logic MUST handle:

- deadlines;
- age eligibility;
- country eligibility;
- education-level eligibility;
- structured language requirements;
- structured funding compatibility;
- completion status;
- hard constraints;
- readiness calculations;
- match calculations;
- gap impact calculations;
- task completion.

Never delegate everything to the LLM.

---

# 10. DATABASE MODELS

Create proper SQLAlchemy models.

## User

Fields:

id  
name  
email  
password_hash  
role  
preferred_language  
country  
created_at  
updated_at

Roles:

student  
admin

---

## StudentProfile

Fields:

id  
user_id  
birth_year  
country  
city  
education_level  
grade_year  
gpa  
gpa_scale  
english_level  
ielts_score  
sat_score  
budget_level  
preferred_countries  
preferred_fields  
skills  
interests  
achievements  
extracurriculars  
volunteering  
research_experience  
work_experience  
created_at  
updated_at

Use normalized related tables where useful.

---

## Goal

Fields:

id  
user_id  
title  
goal_type  
target_field  
target_countries  
target_date  
funding_requirement  
education_level  
language  
description  
status  
created_at  
updated_at

Statuses:

ACTIVE  
PAUSED  
COMPLETED

---

## Requirement

Fields:

id  
goal_id  
category  
name  
description  
target_value  
importance  
source_type  
created_at

Categories:

ACADEMIC  
LANGUAGE  
EXPERIENCE  
EXTRACURRICULAR  
FINANCIAL  
APPLICATION  
SKILL  
ELIGIBILITY

---

## ProfileGap

Fields:

id  
user_id  
goal_id  
requirement_id  
category  
title  
description  
severity  
current_state  
target_state  
status  
evidence  
created_at  
resolved_at

Statuses:

OPEN  
IMPROVING  
RESOLVED

Severity:

LOW  
MEDIUM  
HIGH  
CRITICAL

---

## Opportunity

Fields:

id  
title  
provider  
opportunity_type  
description  
official_url  
country  
delivery_mode  
min_age  
max_age  
eligible_countries  
education_levels  
fields  
funding_type  
funding_amount_text  
cost_text  
language_requirements  
deadline  
start_date  
end_date  
requirements_text  
verified_at  
source_label  
created_at  
updated_at

Opportunity types:

SCHOLARSHIP  
UNIVERSITY_PROGRAM  
OLYMPIAD  
COMPETITION  
RESEARCH  
SUMMER_SCHOOL  
INTERNSHIP  
EXCHANGE  
COURSE  
VOLUNTEERING  
FELLOWSHIP  
LANGUAGE_PROGRAM

---

## OpportunityRequirement

Fields:

id  
opportunity_id  
category  
name  
description  
required  
structured_value

---

## OpportunityMatch

Fields:

id  
user_id  
goal_id  
opportunity_id  
match_score  
eligibility_status  
readiness_score  
impact_score  
explanation  
calculated_at

Eligibility:

ELIGIBLE  
POSSIBLY_ELIGIBLE  
NOT_ELIGIBLE  
UNKNOWN

---

## GapImpact

Fields:

id  
opportunity_match_id  
gap_id  
impact_strength  
reason

Impact:

LOW  
MEDIUM  
HIGH

---

## Roadmap

Fields:

id  
user_id  
goal_id  
title  
created_at  
updated_at

---

## RoadmapTask

Fields:

id  
roadmap_id  
opportunity_id  
gap_id  
title  
description  
category  
priority  
due_date  
status  
estimated_minutes  
created_at  
completed_at

Statuses:

TODO  
IN_PROGRESS  
COMPLETED  
SKIPPED

---

## ReadinessSnapshot

Fields:

id  
user_id  
goal_id  
overall_readiness  
academic_readiness  
language_readiness  
experience_readiness  
extracurricular_readiness  
financial_readiness  
application_readiness  
created_at

---

## ApplicationDocument

Fields:

id  
user_id  
opportunity_id  
document_type  
title  
content  
created_at  
updated_at

Types:

MOTIVATION_LETTER  
PERSONAL_STATEMENT  
CV  
ESSAY  
OTHER

---

## DocumentReview

Fields:

id  
document_id  
overall_score  
requirement_coverage  
strengths  
gaps  
recommendations  
created_at

---

# 11. PROFILE ONBOARDING

The onboarding must be short enough for live demo.

Use a multi-step wizard.

## Step 1 — About You

Name  
Country  
Age or birth year  
Education level  
Grade/year

## Step 2 — Academic Profile

GPA  
Subjects / field interests  
English level  
IELTS / SAT if available

## Step 3 — Experience

Achievements  
Olympiads  
Projects  
Research  
Volunteering  
Extracurriculars

Allow:

None yet

Never shame the user for missing experience.

## Step 4 — Constraints

Budget level  
Preferred countries  
Need financial aid?

## Step 5 — Goal

Ask:

> What are you trying to achieve?

Allow natural-language input.

Example:

> I want to study Chemical Engineering in Europe in English with a full or substantial scholarship.

Button:

# Build My Path

---

# 12. GOAL INTELLIGENCE ENGINE

Convert natural-language goals into structured data.

Example input:

> I want to study Chemical Engineering in Europe in English with a scholarship.

Expected structured output:

```json
{
  "goal_type": "UNIVERSITY_ADMISSION",
  "target_field": "Chemical Engineering",
  "target_regions": ["Europe"],
  "language": "English",
  "funding_requirement": "HIGH",
  "education_level": "BACHELOR",
  "confidence": 0.93
}
```

Validate AI output using Pydantic.

If validation fails:

1. retry once;
2. if it still fails, use deterministic fallback extraction;
3. allow user to edit the result.

The user must always be able to correct AI interpretation.

---

# 13. GAP ENGINE

This is a CORE system.

Compare:

CURRENT PROFILE

against:

TARGET REQUIREMENTS.

Generate structured gaps.

Example:

## LANGUAGE

IELTS evidence missing

Severity:

HIGH

Current:

No official test score

Target:

IELTS 6.5 equivalent

Evidence:

Profile contains no IELTS score while the target requirement requires certified English proficiency.

---

## EXPERIENCE

Limited subject-related project/research evidence

Severity:

MEDIUM

---

## APPLICATION

Motivation letter not prepared

Severity:

MEDIUM

Every gap MUST include evidence.

Never display unsupported conclusions.

---

# 14. PATH MAP / GAP GRAPH

Create route:

`/path`

Visualize:

```text
Chemical Engineering Abroad
│
├── Academic ✓
│
├── Language ⚠
│   └── IELTS missing
│
├── Experience ⚠
│   └── Research exposure
│
├── Financial ⚠
│   └── Funding required
│
└── Application ⚠
    └── Motivation Letter
```

The graph must be:

- responsive;
- clickable;
- understandable;
- reliable.

Do not introduce a complex graph library unless necessary.

Clicking a gap opens:

- why it matters;
- current state;
- target state;
- evidence;
- opportunities that can help close it.

---

# 15. OPPORTUNITY DATABASE

Seed at least:

# 40 meaningful opportunities

Prefer:

50–60.

Minimum:

10 scholarships  
8 university programs  
5 competitions / olympiads  
5 research / summer programs  
5 internships / volunteering opportunities  
5 courses / language opportunities

Each seeded opportunity must have:

- title;
- provider;
- type;
- description;
- eligibility;
- fields;
- country;
- deadline;
- funding;
- requirements;
- official URL OR clear demo-source label;
- gap categories it may help address.

Do NOT claim demo data is live/current.

If historical or demo data is used, label it clearly:

Demo dataset

Architecture must support future ingestion from verified sources.

For demo reliability, use future deadlines relative to seed execution date where practical.

Example:

deadline = today + 45 days.

---

# 16. ELIGIBILITY ENGINE

Hard filters must evaluate:

- country restrictions;
- age;
- education level;
- deadline;
- field restrictions;
- explicit language requirements.

Output:

ELIGIBLE  
POSSIBLY_ELIGIBLE  
NOT_ELIGIBLE  
UNKNOWN

Always explain failed hard requirements.

Example:

> Program requires applicants to be at least 18. Current profile indicates age 16.

A high Match Score must NEVER override hard ineligibility.

---

# 17. MATCH SCORE

Match Score answers:

> How well does this opportunity align with the user's goal and profile?

Implement deterministic scoring.

Use configurable weights.

Example:

```text
goal relevance          0.30
field relevance         0.20
location relevance      0.10
funding relevance       0.15
profile compatibility   0.15
gap impact              0.10
```

Store weights centrally in:

`backend/app/config/scoring.py`

Return:

0–100.

Do not scatter magic coefficients throughout the project.

---

# 18. READINESS SCORE

Readiness answers:

> How prepared is the user to pursue this goal/opportunity right now?

Readiness is NOT Match Score.

Readiness is NOT admission probability.

Calculate:

Academic Readiness  
Language Readiness  
Experience Readiness  
Extracurricular Readiness  
Financial Readiness  
Application Readiness

Example:

Overall Readiness: 61%

Academic: 84%  
Language: 55%  
Experience: 42%  
Extracurricular: 73%  
Financial: 68%  
Application: 28%

Suggested MVP formula:

```text
overall_readiness =
academic * 0.25
+ language * 0.15
+ experience * 0.20
+ extracurricular * 0.10
+ financial * 0.10
+ application * 0.20
```

All coefficients must be centrally configurable.

UI wording:

> Estimated readiness based on your current profile and known requirements.

NEVER say:

> You have a 61% chance of admission.

Every score must be explainable.

Clicking a score should show:

- evidence;
- missing requirements;
- actions that can improve it.

---

# 19. OPPORTUNITY GAP IMPACT

This is one of the MAIN product differentiators.

Calculate:

> How strongly could this opportunity help close the user's current gaps?

Example:

Research Summer School

Match: 83%

Readiness: 76%

Gap Impact:

HIGH

Closes:

Research Experience Gap — HIGH

Subject Exploration Gap — MEDIUM

Explain why.

Gap Impact should be visually prominent.

---

# 20. OPPORTUNITY FEED

Create:

`/opportunities`

Default sorting:

# Recommended for your path

Search:

title  
provider  
field  
description

Filters:

Type  
Country  
Funding  
Field  
Deadline  
Delivery Mode  
Eligibility

Sorting:

Recommended  
Highest Match  
Highest Gap Impact  
Nearest Deadline  
Highest Readiness

Opportunity cards show:

Title  
Provider  
Type  
Deadline  
Funding  
Match  
Readiness  
Gap Impact  
Eligibility

Also show:

# Why this matters for you

Example:

> Strong fit because it can help close your research-experience gap while aligning with your engineering goal.

---

# 21. OPPORTUNITY DETAIL PAGE

Route:

`/opportunities/:id`

Sections:

Overview  
Eligibility  
Requirements  
Funding  
Deadline  
Why it matches you  
Your gaps  
Potential gap impact  
Your readiness  
Recommended actions  
Official source

Buttons:

Add to Roadmap  
Start Preparation  
Open Official Page

Never fabricate official information through AI.

Structured opportunity facts must come from stored database records.

---

# 22. ROADMAP ENGINE

Build a backward plan from deadlines.

Example:

```text
15 Dec — Submit application
08 Dec — Final application review
01 Dec — Request recommendation
20 Nov — Complete English requirement
12 Nov — Draft motivation letter
05 Nov — Collect documents
Today  — Start preparation
```

Roadmap generation combines:

deterministic deadline logic

+

AI-generated descriptions where useful.

AI MUST NOT invent deadlines.

---

# 23. DYNAMIC ROADMAP

When the user:

- completes a task;
- changes profile data;
- adds an achievement;
- completes an opportunity;
- changes a goal;

the system must recalculate:

- gaps;
- readiness;
- recommendations;
- roadmap priorities.

Preserve historical information.

Do not simply delete old history.

---

# 24. PROGRESS ENGINE

Example:

User adds:

IELTS 7.0.

System must:

1. update profile;
2. reevaluate language requirement;
3. improve or resolve related gap;
4. recalculate language readiness;
5. recalculate overall readiness;
6. create ReadinessSnapshot;
7. update recommendations;
8. update roadmap priorities.

This MUST happen through backend business logic.

Do not merely animate a number in frontend.

---

# 25. DASHBOARD

Route:

`/dashboard`

The first screen must answer:

# Where am I?

# Where am I going?

# What is stopping me?

# What should I do next?

Sections:

## Active Goal

Example:

Chemical Engineering Abroad

Bachelor

Funding needed: High

## Overall Readiness

Example:

67%

with category breakdown.

## Biggest Current Gaps

Top 3.

Example:

1. Research experience
2. English certification
3. Application materials

## Best Next Action

Example:

> Complete your IELTS registration before 14 October.

## Opportunities That Move You Forward

Show 3–5.

## Roadmap

Upcoming tasks and deadlines.

## Progress

Readiness history chart.

Avoid clutter.

---

# 26. EXPLAINABILITY

Every major recommendation must be explainable.

The user should be able to understand:

Why this opportunity?

Why this gap?

Why this score?

Why this task?

Example:

> Your goal requires stronger subject-related experience. This research program matches your target field and directly addresses the experience gap currently identified in your profile.

---

# 27. AI PATH ADVISOR

Create:

`/advisor`

It knows:

- user profile;
- active goal;
- current gaps;
- recommended/saved opportunities;
- roadmap;
- readiness.

Example questions:

> What should I focus on this month?

> Why is my readiness only 61%?

> Should I prioritize IELTS or research experience?

> Which opportunity would improve my profile most?

Ground responses in platform data.

Distinguish:

known platform data

from:

general advice.

Do not invent opportunities or deadlines and present them as database facts.

---

# 28. APPLICATION REVIEWER

Create:

`/applications/review`

Flow:

1. user selects opportunity;
2. selects document type;
3. pastes text;
4. clicks Review.

AI receives:

- document;
- stored requirements for selected opportunity;
- document type.

Return structured JSON:

```json
{
  "overall_score": 0,
  "requirement_coverage": [
    {
      "requirement": "...",
      "coverage": 0,
      "evidence": "...",
      "recommendation": "..."
    }
  ],
  "strengths": [],
  "gaps": [],
  "recommendations": []
}
```

Do NOT fabricate experience.

Do NOT rewrite essays by inventing achievements.

---

# 29. AI PROMPT ARCHITECTURE

Store prompts separately:

```text
backend/app/prompts/
  goal_parser.txt
  gap_explainer.txt
  opportunity_explainer.txt
  roadmap_explainer.txt
  application_reviewer.txt
  advisor.txt
```

Each prompt should contain:

ROLE  
CONTEXT  
INPUT  
TASK  
RULES  
OUTPUT FORMAT  
EXAMPLES

Do not bury long prompts inside React components.

---

# 30. STRUCTURED AI OUTPUT

AI calls used for business workflows must return structured output where applicable.

Pipeline:

AI response  
↓  
JSON parse  
↓  
Pydantic validation  
↓  
success

If invalid:

retry once with correction instruction.

If still invalid:

safe fallback.

Never crash because an LLM returned malformed JSON.

---

# 31. MOCK AI PROVIDER

Demo Mode is mandatory.

Mock AI must NOT return:

> Mock response.

It must provide realistic deterministic outputs.

For the seeded demo user, support:

- goal parsing;
- gap explanations;
- opportunity explanations;
- roadmap explanations;
- application review;
- advisor answers.

Matching, readiness and other deterministic calculations remain real backend logic.

---

# 32. DEMO PERSONA

Seed:

Name:

Aruzhan Demo

Country:

Kazakhstan

Age:

16

Education:

High School / Grade 11

Academic profile:

Strong chemistry and mathematics.

English:

B2

IELTS:

Not yet taken.

Experience:

School chemistry project.

Volunteering:

One activity.

Research:

None.

Financial:

Needs substantial financial support.

Goal:

> Study Chemical Engineering in Europe in English with substantial financial support.

Seed enough linked data so the dashboard is immediately meaningful.

---

# 33. DEMO ACCOUNT

Create:

```text
student@demo.com
Demo123!
```

Document credentials in README.

Demo user must already have:

- active goal;
- profile;
- several gaps;
- readiness snapshots;
- recommended opportunities;
- roadmap;
- some history.

A brand-new user must also be able to complete onboarding from scratch.

---

# 34. REQUIRED LIVE DEMO FLOW

This flow MUST work without manual database editing:

Landing  
↓  
Explore Demo  
↓  
Demo login  
↓  
Dashboard  
↓  
Active Goal  
↓  
Readiness  
↓  
Path Map  
↓  
Experience Gap  
↓  
Recommended Opportunity  
↓  
Match + Readiness + Gap Impact  
↓  
Add to Roadmap  
↓  
Roadmap updates  
↓  
Update profile or complete task  
↓  
Backend recalculates readiness  
↓  
Dashboard visibly changes  
↓  
Application Reviewer  
↓  
Requirement-specific AI feedback

The demo must show a REAL state change.

Values must be calculated.

Do not hardcode the before/after result into UI.

---

# 35. LANDING PAGE

Build a professional SaaS / EdTech landing page.

Hero:

# Your goal is the destination.
# We build the path.

Subtitle:

> Pathly identifies the gaps between where you are and where you want to be, then finds educational opportunities that move you forward.

Primary CTA:

Build My Path

Secondary CTA:

Explore Demo

Sections:

Problem  
How It Works  
Gap Graph  
Opportunity Matching  
Dynamic Readiness  
Roadmap  
Example Journey  
CTA

How It Works:

Set your goal  
→ Map your gaps  
→ Discover opportunities  
→ Take action  
→ Watch your readiness grow

---

# 36. DESIGN

Design must look like a real modern EdTech/SaaS product.

Style:

clean  
professional  
trustworthy  
academic  
modern  
minimal  
premium  
data-driven

Do NOT make it childish.

Suggested palette:

Primary Navy: `#0B1F3A`

Deep Navy: `#07152A`

Primary Blue: `#2563EB`

Light Blue: `#EFF6FF`

Background: `#F8FAFC`

White: `#FFFFFF`

Text: `#172033`

Muted: `#64748B`

Border: `#E2E8F0`

Success: `#16A34A`

Warning: `#F59E0B`

Danger: `#DC2626`

Avoid excessive gradients.

Use:

- subtle borders;
- rounded cards;
- restrained shadows;
- clear typography;
- whitespace;
- consistent spacing.

---

# 37. READINESS VISUALIZATION

Use understandable indicators.

Example:

```text
Academic
████████░░ 82%

Language
██████░░░░ 61%

Experience
████░░░░░░ 43%

Application
██░░░░░░░░ 22%
```

Always include labels.

Do not rely only on color.

---

# 38. RESPONSIVE DESIGN

Support:

desktop  
laptop  
tablet  
mobile

Mobile:

sidebar → menu/drawer

cards → stacked

tables → horizontally scrollable or cards

charts → responsive

forms → touch friendly

No horizontal overflow.

---

# 39. ACCESSIBILITY

Implement:

semantic HTML  
form labels  
keyboard navigation  
visible focus states  
sufficient contrast  
ARIA where appropriate  
accessible modals  
accessible buttons

Scores must not rely only on color.

---

# 40. FRONTEND STRUCTURE

Suggested:

```text
frontend/src/

components/
  ui/
  layout/
  dashboard/
  goals/
  gaps/
  opportunities/
  roadmap/
  advisor/
  applications/
  charts/

pages/
  LandingPage.tsx
  LoginPage.tsx
  RegisterPage.tsx
  OnboardingPage.tsx
  DashboardPage.tsx
  GoalPage.tsx
  PathMapPage.tsx
  OpportunitiesPage.tsx
  OpportunityDetailPage.tsx
  RoadmapPage.tsx
  AdvisorPage.tsx
  ApplicationReviewerPage.tsx
  ProfilePage.tsx

hooks/
services/
types/
utils/
contexts/

App.tsx
```

Use reusable components.

Avoid giant page components.

---

# 41. BACKEND STRUCTURE

Suggested:

```text
backend/app/

api/
  auth.py
  profile.py
  goals.py
  gaps.py
  opportunities.py
  roadmap.py
  progress.py
  advisor.py
  applications.py
  dashboard.py

models/
schemas/

services/
  auth_service.py
  profile_service.py
  goal_service.py
  requirement_service.py
  gap_service.py
  eligibility_service.py
  matching_service.py
  readiness_service.py
  impact_service.py
  roadmap_service.py
  progress_service.py
  application_service.py

ai/
  provider.py
  real_provider.py
  mock_provider.py
  goal_parser.py
  gap_explainer.py
  advisor.py
  application_reviewer.py

prompts/

config/
  settings.py
  scoring.py

database/
  base.py
  session.py

main.py
```

Keep API, business logic, AI, database and scoring separated.

---

# 42. REQUIRED API ENDPOINTS

## Authentication

POST `/api/auth/register`

POST `/api/auth/login`

GET `/api/auth/me`

## Profile

GET `/api/profile`

PUT `/api/profile`

POST `/api/profile/achievement`

## Goals

GET `/api/goals`

POST `/api/goals`

GET `/api/goals/{id}`

PUT `/api/goals/{id}`

POST `/api/goals/{id}/activate`

## Gap Analysis

POST `/api/goals/{id}/analyze`

GET `/api/goals/{id}/gaps`

## Readiness

GET `/api/goals/{id}/readiness`

GET `/api/goals/{id}/readiness/history`

## Opportunities

GET `/api/opportunities`

GET `/api/opportunities/{id}`

GET `/api/goals/{id}/recommendations`

POST `/api/opportunities/{id}/recalculate`

## Roadmap

GET `/api/goals/{id}/roadmap`

POST `/api/goals/{id}/roadmap/generate`

POST `/api/roadmap/tasks/{id}/complete`

PUT `/api/roadmap/tasks/{id}`

## Dashboard

GET `/api/dashboard`

## AI

POST `/api/ai/parse-goal`

POST `/api/ai/advisor`

## Application Review

POST `/api/applications/review`

GET `/api/applications/reviews`

## Health

GET `/api/health`

All endpoints must use:

- Pydantic request schemas;
- Pydantic response schemas;
- authentication where necessary;
- authorization where necessary;
- validation;
- controlled error handling.

---

# 43. AUTHENTICATION

Implement:

Register  
Login  
Logout  
Current user  
Protected routes

Use JWT.

Passwords must be securely hashed.

Never store plaintext passwords.

Frontend protected routes redirect unauthorized users.

Backend remains the real security boundary.

---

# 44. SCORING CONFIGURATION

Create:

`backend/app/config/scoring.py`

Put important weights and thresholds there.

Examples:

MATCH_WEIGHTS

READINESS_WEIGHTS

GAP_SEVERITY_THRESHOLDS

IMPACT_THRESHOLDS

Do not scatter magic numbers.

---

# 45. DEADLINE LOGIC

Handle:

future deadlines  
passed deadlines  
unknown deadlines

Passed opportunities must be clearly marked.

Do not recommend expired opportunities as active next steps.

For demo data, use relative future dates where practical.

---

# 46. SOURCE INTEGRITY

The product must never pretend AI-generated information is verified official information.

Each opportunity should show:

Source

Last verified

If demo:

Demo dataset

If official URL exists:

Open Official Source

AI may interpret stored requirements but must not silently alter them.

---

# 47. DASHBOARD CHARTS

Use Recharts.

Include:

## Readiness Over Time

Line chart using ReadinessSnapshot.

## Readiness Breakdown

Bar chart or radar chart.

## Gap Distribution

Simple bar/donut chart.

All chart values must come from backend data.

No static chart values.

---

# 48. ERROR HANDLING

Frontend:

- loading states;
- empty states;
- API errors;
- retry;
- toast notifications;
- disabled submit while request is pending;
- form validation.

Backend:

- validation errors;
- authentication errors;
- authorization errors;
- database errors;
- AI timeout;
- malformed AI JSON;
- missing data;
- expired opportunity;
- invalid state transitions.

Never expose stack traces to end users.

---

# 49. LOADING STATES

Examples:

> Analyzing your goal...

> Mapping your current gaps...

> Finding opportunities that move you forward...

> Building your roadmap...

> Reviewing your application against program requirements...

Use skeletons/spinners appropriately.

---

# 50. EMPTY STATES

No goal:

> Start by telling us where you want to go.

No opportunities:

> We couldn't find a strong match with the current filters. Try broadening your preferences.

No roadmap:

> Add an opportunity or generate a roadmap for your active goal.

No gaps:

> Your current profile covers the requirements we know about. Continue building evidence and keep your profile updated.

---

# 51. SECURITY

Implement:

secure password hashing  
JWT  
input validation  
ORM  
protected API  
CORS  
environment secrets  
reasonable token expiration  
authorization

Do not expose:

AI API key  
JWT secret  
password hashes

Do not log sensitive secrets.

---

# 52. PRIVACY

Store only information necessary for educational recommendations.

Do not collect:

camera  
microphone  
browser history  
private messages  
unrelated personal data

If feasible, implement basic account deletion.

---

# 53. DATA ETHICS

Never present Readiness Score as admission probability.

Never say:

> You have a 72% chance of getting into this university.

Instead:

> Your current readiness is estimated at 72% based on the requirements and profile information available.

Never guarantee:

admission  
scholarship  
competition results

---

# 54. INTERNATIONALIZATION

Prepare architecture for localization.

English is mandatory.

Russian may be implemented if it can be done cleanly without destabilizing core functionality.

Do not duplicate business logic for languages.

---

# 55. REQUIRED ROUTES

At minimum:

```text
/
/login
/register
/onboarding
/dashboard
/goal/:id
/path
/opportunities
/opportunities/:id
/roadmap
/advisor
/applications/review
/profile
```

---

# 56. MAIN NAVIGATION

Authenticated navigation:

Dashboard  
My Path  
Opportunities  
Roadmap  
AI Advisor  
Application Review  
Profile

Keep navigation simple.

---

# 57. PRODUCT COPY

Avoid generic AI marketing.

Bad:

> Unlock your potential with the power of AI.

Prefer:

> See what is missing from your profile.

> Find opportunities that close your gaps.

> Know what to do next.

> Your readiness changed because you completed a language requirement.

---

# 58. MAIN DEMO MOMENT

Initial state:

IELTS = missing.

Language gap exists.

Readiness example:

61%

User updates profile:

IELTS = 7.0.

Backend recalculates.

Language gap changes.

Readiness increases.

ReadinessSnapshot is created.

Recommendations may update.

Dashboard visibly changes.

This must be real application behavior.

---

# 59. SECOND DEMO MOMENT

Open recommended research opportunity.

Display:

Match: 89%

Readiness: 74%

Gap Impact: HIGH

Show:

# Why this matters

> This opportunity directly addresses your current research-experience gap and aligns with your Chemical Engineering goal.

Click:

Add to Roadmap

Roadmap must actually update.

---

# 60. THIRD DEMO MOMENT

Open Application Review.

Select seeded scholarship.

Paste demo motivation letter.

AI analyzes against stored requirements.

Example display:

Leadership coverage: 80%

Academic motivation: 92%

Community impact: 35%

Feedback:

> Your community-impact evidence is currently weak. Add a concrete example and measurable outcome if one exists.

Do not invent one.

---

# 61. DO NOT BUILD

Do not waste MVP time on:

social network  
user-to-user chat  
video calls  
mentor marketplace  
payments  
complex admin CMS  
blockchain  
gamification economy  
native mobile app  
scraping dozens of websites  
unnecessary microservices

Focus on the core value loop.

---

# 62. NON-NEGOTIABLE FUNCTIONAL REQUIREMENTS

Every important visible button must work.

No:

fake CTA  
dead navigation  
fake filters  
fake charts  
fake readiness  
fake recommendations  
fake AI  
fake roadmap

Demo mode may use seeded data and MockAIProvider.

However:

application state must be real.

calculations must be real.

database persistence must be real.

---

# 63. CODE QUALITY

Code must be:

modular  
typed  
readable  
testable  
maintainable

Avoid giant files.

Use clear domain boundaries.

Frontend TypeScript:

avoid unnecessary `any`.

Backend:

use type hints.

Use schemas rather than arbitrary dictionaries where practical.

---

# 64. TESTING

Testing is mandatory.

## Backend Unit Tests

Test:

eligibility engine  
match score  
readiness calculation  
gap severity  
gap impact  
roadmap deadline ordering  
progress recalculation

## API Tests

Test:

register  
login  
profile update  
goal creation  
gap analysis  
recommendations  
roadmap generation  
task completion  
dashboard update  
application review  
authorization

## AI Tests

Test:

MockAIProvider

malformed AI output fallback

provider failure fallback

## Frontend

At minimum:

TypeScript compilation

production build

If practical, add focused component/integration tests.

---

# 65. CRITICAL TEST — READINESS RECALCULATION

Initial:

IELTS = null

Then update:

IELTS = 7.0

Expected:

language gap improves/resolves where relevant;

language readiness increases;

overall readiness recalculates;

ReadinessSnapshot is created.

Test backend state.

Do not merely test frontend animation.

---

# 66. CRITICAL TEST — GAP IMPACT

Demo user has:

Experience Gap.

Opportunity:

Research Summer Program.

Expected:

Gap Impact on Experience Gap = HIGH.

An unrelated language course must NOT receive the same impact.

---

# 67. CRITICAL TEST — HARD ELIGIBILITY

If:

opportunity min_age = 18

and:

user age = 16

result:

NOT_ELIGIBLE

with explicit reason.

Match Score must not override hard ineligibility.

---

# 68. SEED DATA

Create idempotent seed script.

Seed:

demo user  
demo profile  
demo goal  
requirements  
gaps  
roadmap  
readiness history  
40+ opportunities

Running seed multiple times must not duplicate everything.

---

# 69. README

README is part of the judged deliverable.

Include:

Pathly

Problem

Solution

Core Innovation

Opportunity-to-Gap Matching

Architecture

Tech Stack

Features

Project Structure

Quick Start

Environment Variables

Database

Seed Data

Demo Account

Demo Mode

Real AI Configuration

Running Backend

Running Frontend

Docker

Testing

API Documentation

Matching Algorithm

Readiness Algorithm

Gap Impact Algorithm

AI Architecture

Source Integrity

Security

Known MVP Limitations

Future Development

3-Minute Demo

---

# 70. README QUICK START

Put a very visible:

# Quick Start

near the top.

Prefer:

```bash
cp .env.example .env
docker compose up --build
```

or equally simple verified commands.

Clearly show:

Demo:

```text
student@demo.com
Demo123!
```

App URL.

API docs URL.

---

# 71. ENVIRONMENT

Create:

`.env.example`

Example:

```env
DATABASE_URL=sqlite:///./pathly.db
JWT_SECRET=replace_me
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=
AI_BASE_URL=
FRONTEND_URL=http://localhost:5173
VITE_API_URL=http://localhost:8000
```

Never commit secrets.

---

# 72. GIT

Create:

`.gitignore`

Exclude:

.env  
runtime DB files where appropriate  
node_modules  
dist  
__pycache__  
.pytest_cache  
coverage files  
IDE files  
OS files

Do not exclude:

.env.example  
README  
migrations  
seed scripts

Repository must be clean and understandable.

---

# 73. DOCKER

Provide:

backend Dockerfile

frontend Dockerfile if needed

docker-compose.yml

Preferred judge setup:

```bash
docker compose up --build
```

If Docker is unavailable in the execution environment, still verify the project using native commands.

---

# 74. DEPLOYMENT READINESS

Repository should be suitable for deployment to services such as:

Render  
Railway  
Fly.io  
Vercel + backend hosting

Do not hardcode localhost API URLs.

Frontend API base URL must come from environment configuration.

Use:

VITE_API_URL

Configure production CORS through environment variables.

---

# 75. HEALTH ENDPOINT

Create:

GET `/api/health`

Return something like:

```json
{
  "status": "ok",
  "database": "ok",
  "ai_provider": "mock"
}
```

Never expose secrets.

---

# 76. PERSISTENCE

Important state must persist after browser refresh.

Do NOT store core state only in React memory.

These must persist in backend/database:

Profile

Goal

Roadmap

Tasks

Readiness

Reviews

---

# 77. ACCEPTANCE CRITERIA — NEW USER

A completely new user can:

Register  
→ Complete onboarding  
→ Describe goal  
→ AI parses goal  
→ Confirm/edit parsed goal  
→ Generate Path  
→ See gaps  
→ See readiness  
→ See recommended opportunities  
→ Open opportunity  
→ Understand why it matters  
→ Add to roadmap  
→ Complete/update an action  
→ See readiness recalculated

without manual database intervention.

---

# 78. ACCEPTANCE CRITERIA — DEMO USER

Judge can:

Explore Demo  
→ Open populated dashboard  
→ Understand goal in under 30 seconds  
→ See readiness  
→ See biggest gaps  
→ Open Path Map  
→ Open recommended opportunity  
→ See Match / Readiness / Gap Impact  
→ Add opportunity to roadmap  
→ Update profile  
→ See actual recalculation  
→ Use AI Advisor  
→ Use Application Reviewer

without entering an API key.

---

# 79. ACCEPTANCE CRITERIA — SYSTEM

System automatically:

stores profile;

stores goal;

generates requirements;

detects gaps;

calculates eligibility;

calculates match;

calculates readiness;

calculates gap impact;

ranks opportunities;

generates roadmap;

stores tasks;

updates completed tasks;

recalculates readiness;

stores historical snapshots;

updates dashboard;

uses AI abstraction;

falls back to Demo AI.

---

# 80. FAILURE RESILIENCE

Test behavior when:

AI API unavailable

AI response malformed

database empty

opportunity expired

user profile incomplete

goal parsing fails

no matching opportunities

API request fails

user refreshes page

JWT invalid

frontend starts before backend

The app should fail gracefully.

---

# 81. CLEAN INSTALL TEST

Before declaring completion, simulate a clean setup as closely as possible.

Verify:

dependencies install;

environment example is sufficient;

database initializes;

migrations run;

seed runs;

backend starts;

frontend starts;

login works;

demo account works.

---

# 82. BACKEND FINAL CHECK

Run:

tests

startup/import checks

Confirm:

database initialization works;

migrations work;

seed works;

authentication works;

API works;

AI fallback works;

no unhandled startup exceptions.

---

# 83. FRONTEND FINAL CHECK

Run:

npm install

TypeScript check

production build

Fix all:

TypeScript errors

missing imports

broken routes

invalid API types

build errors

Do NOT ignore build failures.

---

# 84. INTEGRATION CHECK

Start the actual application.

Test:

frontend → backend

Verify:

register/login

dashboard

profile

goal

gap analysis

opportunity recommendations

roadmap

task completion

readiness update

AI demo

application review

---

# 85. E2E TESTING

If browser automation such as Playwright is available, create at least one smoke E2E test covering:

Explore Demo  
→ Dashboard  
→ Opportunity  
→ Roadmap

and one state-changing path where practical.

If browser automation cannot run, document that limitation but perform all other integration checks.

---

# 86. NO SILENT TEST FAILURES

Do NOT:

disable failing tests;

comment tests out;

replace real assertions with `assert True`;

use TypeScript suppression to hide systemic errors;

silence build errors;

skip core tests merely to claim success.

Fix the underlying problem.

---

# 87. FINAL VERIFICATION REPORT

Before finishing, produce:

```text
Backend tests: PASS / FAIL

Frontend typecheck: PASS / FAIL

Frontend production build: PASS / FAIL

Seed: PASS / FAIL

Demo login: PASS / FAIL

Main API flow: PASS / FAIL

AI Mock Mode: PASS / FAIL

Real AI provider integration: IMPLEMENTED / NOT IMPLEMENTED

Docker: PASS / FAIL / NOT AVAILABLE

E2E: PASS / FAIL / NOT AVAILABLE
```

Do not claim PASS unless the command actually succeeded.

---

# 88. REAL AI DISTINCTION

A real AI provider can be fully IMPLEMENTED without being live-tested if no API key exists in the coding environment.

If no API key exists:

do not invent one;

do not commit one;

do not claim real-provider test PASS.

Instead verify:

provider code exists;

configuration exists;

request/response validation exists;

fallback exists;

Mock Mode works.

README must explain exactly how the owner enables real AI through environment variables.

---

# 89. REPOSITORY DELIVERY

The repository must contain everything required for another developer or judge to clone and run it.

No dependency on:

files outside repository;

local absolute paths;

hidden manually created database;

uncommitted configuration;

secret keys.

A fresh clone must be reproducible using README instructions.

---

# 90. JUDGE-FRIENDLY README

Include:

# 3-Minute Demo

Exact steps:

1. Open demo account.
2. View current readiness.
3. Open Path Map.
4. Inspect Experience Gap.
5. Open recommended research opportunity.
6. Observe Match / Readiness / Gap Impact.
7. Add it to Roadmap.
8. Update a profile requirement.
9. Observe readiness recalculation.
10. Open Application Reviewer.

---

# 91. MVP LIMITATIONS

Be transparent.

README should explain:

- seeded opportunities are used for reliable hackathon demonstration;
- Readiness is a heuristic progress metric, not admission probability;
- opportunity information should be verified against official sources;
- production version requires verified data ingestion/update pipelines;
- AI advice does not guarantee admission or scholarship outcomes.

---

# 92. FUTURE DEVELOPMENT

Document but do not prioritize over core MVP:

verified opportunity ingestion;

institution integrations;

school counselor dashboard;

notifications;

calendar synchronization;

verified application-requirement extraction;

multilingual recommendation engine;

mentor integration;

exam-preparation pathways;

longitudinal outcomes measurement.

---

# 93. PRIORITY ORDER

## P0 — MUST WORK

Authentication

Profile

Goal

Gap Engine

Opportunity Database

Eligibility

Matching

Readiness

Gap Impact

Dashboard

Opportunity Detail

Roadmap

Progress / Recalculation

Mock AI

Real AI abstraction/provider

README

Tests

Clean startup

## P1

Path Map

Application Reviewer

AI Advisor

Charts

Advanced filtering

## P2

Additional visual polish

Extra analytics

Additional opportunity categories

Localization

Never sacrifice P0 stability for P2 polish.

---

# 94. DEFINITION OF DONE

The project is NOT done when:

files exist.

The project is NOT done when:

the frontend looks good.

The project is NOT done when:

tests were written but never executed.

The project is NOT done when:

most functionality “should work”.

The project is done only when:

the repository contains a functional MVP and all available critical verification checks have actually been executed successfully.

---

# 95. FINAL EXECUTION INSTRUCTION

Begin implementation directly in the CURRENT repository.

Do NOT respond only with a plan.

First inspect the repository.

Preserve useful existing work if present.

If the repository is empty, initialize the complete project.

Then execute in this order:

1. Inspect repository.
2. Establish project structure.
3. Create backend.
4. Configure database.
5. Create migrations.
6. Implement authentication.
7. Implement profile.
8. Implement goals.
9. Implement requirements.
10. Implement Gap Engine.
11. Implement Opportunity models.
12. Implement seed data.
13. Implement Eligibility Engine.
14. Implement Matching Engine.
15. Implement Readiness Engine.
16. Implement Gap Impact Engine.
17. Implement roadmap.
18. Implement progress/recalculation.
19. Implement AI provider abstraction.
20. Implement MockAIProvider.
21. Implement RealAIProvider.
22. Implement structured AI schemas.
23. Implement AI prompts.
24. Implement frontend.
25. Implement onboarding.
26. Implement dashboard.
27. Implement Path Map.
28. Implement opportunities.
29. Implement opportunity detail.
30. Implement roadmap UI.
31. Implement AI Advisor.
32. Implement Application Reviewer.
33. Implement charts.
34. Implement responsive/accessibility behavior.
35. Implement tests.
36. Implement Docker/deployment configuration.
37. Write README.
38. Run backend tests.
39. Run frontend typecheck.
40. Run frontend production build.
41. Initialize a fresh database.
42. Run seed.
43. Start backend.
44. Start frontend.
45. Verify health endpoint.
46. Verify demo login.
47. Test main user flow.
48. Test state-changing readiness recalculation.
49. Test AI fallback.
50. Fix every discovered runtime/build/type/integration error.
51. Rerun failed checks.
52. Repeat until all available critical checks pass.

Do NOT stop at the first error.

Do NOT ask the user to manually fix code that you can fix yourself.

Do NOT replace difficult functionality with static UI.

When a technical decision is unspecified, choose the simplest reliable solution consistent with this specification.

At the very end provide:

1. concise description of what was implemented;
2. exact commands to run the project;
3. demo credentials;
4. environment variables required for real AI;
5. verification report with actual PASS/FAIL status;
6. genuine remaining limitations.

The final deliverable must be a repository that can be committed to GitHub and submitted for hackathon evaluation without requiring the owner to finish the core implementation manually.
