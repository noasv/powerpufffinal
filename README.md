# Pathly

**Pathly is a navigation system for educational development.** Students choose a destination; Pathly identifies evidence gaps, ranks opportunities by how well they close those gaps, and recalculates the route when the profile changes.

# Quick Start

```bash
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5173**. API docs: **http://localhost:8000/docs**.

**Demo account:** `student@demo.com` / `Demo123!`

## Problem, solution, and core innovation

Opportunity lists answer “what exists?” Pathly answers “given my goal and missing evidence, what should I do next, and why?” Its core **Opportunity-to-Gap Matching** connects profile evidence and destination requirements to opportunities that can improve the route. Readiness is a heuristic progress metric, never an admission probability.

## Features

- JWT register/login, protected APIs, Argon2 password hashing, account deletion.
- Five-step onboarding and editable AI-interpreted structured goals.
- Requirements, evidence-backed gaps, eligibility, centrally configured match/readiness/impact scoring.
- 50 meaningful seeded demo opportunities with relative future deadlines and explicit source labels.
- Dashboard with live readiness history/breakdown, path map, search/filter/sort, opportunity detail.
- Persisted deadline-driven roadmaps and completion actions.
- Profile changes (including the IELTS demo) recalculate gaps/readiness and preserve snapshots.
- Contextual AI advisor and requirement-grounded document review.
- Real OpenAI-compatible provider with retry and automatic Demo AI fallback.

## Architecture and project structure

React + TypeScript + Vite + Tailwind, TanStack Query, Router, and Recharts live in `frontend/`. FastAPI, Pydantic, SQLAlchemy, Alembic, JWT, deterministic services, AI adapters, tests, and seeding live in `backend/`. SQLite is default; set a SQLAlchemy PostgreSQL `DATABASE_URL` without changing business logic.

```text
backend/app/{config,services,main.py,models.py,seed.py}
backend/{alembic,tests,Dockerfile}
frontend/src/{main.tsx,api.ts,index.css}
docker-compose.yml
```

## Native development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

In another shell:

```bash
cd frontend
npm install
npm run dev
```

## Environment variables and real AI

Copy `.env.example`. `DATABASE_URL`, `JWT_SECRET`, `FRONTEND_URL`, and frontend build-time `VITE_API_URL` configure deployment. Demo AI is chosen when `AI_PROVIDER=mock` or no key exists.

To enable a real OpenAI-compatible provider:

```env
AI_PROVIDER=openai
AI_API_KEY=your_key
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
```

Keys remain backend-only. Real calls use controlled timeout/retry; any provider/JSON failure falls back without breaking the flow. AI interprets text but never changes stored official facts or deterministic eligibility/scoring.

## Database, migrations, and seed data

`alembic upgrade head` creates all tables. `python -m app.seed` is idempotent and creates or updates the demo user, profile, active goal, requirements, evidence gaps, readiness history, roadmap, and 50 canonical opportunities without removing existing users. Eight records are Economics-focused. Records say **Demo dataset** and use future dates relative to seeding. Always verify source data.

## Algorithms

- **Match:** goal .30 + field .20 + location .10 + funding .15 + profile compatibility .15 + gap impact .10.
- **Readiness:** academic .25 + language .15 + experience .20 + extracurricular .10 + financial .10 + application .20.
- **Gap impact:** an opportunity receives high impact only when its structured categories intersect open profile gaps. Hard ineligibility remains visible and cannot be overridden by match.

Weights and thresholds are centralized in `backend/app/config/scoring.py`.

## Testing

```bash
cd backend && pytest -q
cd frontend && npm install && npm run typecheck && npm run build
```

Health: `curl http://localhost:8000/api/health`. Swagger provides interactive API documentation. Tests cover authentication/authorization, profile-goal-gap flow, hard age eligibility, gap impact, readiness snapshot recalculation, Mock AI, malformed output fallback, roadmap access, and dashboard integration.

## Docker and deployment

`docker compose up --build` migrates, seeds, and starts both services with persistent SQLite storage. For Render/Railway/Fly, deploy the backend Dockerfile with a durable database and explicit CORS URL. The frontend image is an SPA-capable Nginx build; provide `VITE_API_URL` at build time. PostgreSQL requires installing an appropriate DB driver in production.

## Security and source integrity

Passwords are Argon2 hashes; JWTs expire after 12 hours; APIs enforce ownership; Pydantic validates input; ORM queries avoid raw user SQL; secrets are environment-only. AI keys/hashes are never returned. AI must not be treated as authoritative. Stored demo opportunity information is visibly labeled and official links must be checked.

## Real opportunity discovery

Advisor opportunity searches and typed searches on **Opportunities** share one backend pipeline: deterministic query parsing → an `OpportunityDiscoveryProvider` → URL/title validation → normalization and deduplication → persistence/upsert → the existing eligibility, field relevance, Match, Readiness, and Gap Impact engines. The AI provider is separate: it may explain only the candidate IDs supplied by discovery and cannot create an opportunity record or replace its stored facts.

The production adapter uses a server-side [Serper](https://serper.dev/)-compatible web search response. Configure it in the backend environment:

```env
OPPORTUNITY_DISCOVERY_PROVIDER=serper
OPPORTUNITY_SEARCH_API_KEY=your_server_side_key
OPPORTUNITY_SEARCH_BASE_URL=https://google.serper.dev/search
OPPORTUNITY_SEARCH_TIMEOUT_SECONDS=10
```

No discovery credential is sent to the browser. Without a key—or after a timeout, HTTP error, or malformed response—the application remains available and searches the offline dataset, but every returned record is labeled **Demo opportunity** and the Advisor reports that live discovery was unavailable. A subject/type search is strict: an empty result is shown rather than substituting IELTS, volunteering, or another unrelated type.

Verification states have deliberately narrow meanings:

* `VERIFIED`: reserved for a future validator that confirms an official first-party page; an LLM or search result alone cannot assign this status.
* `SOURCE_FOUND`: an external search result with valid HTTP(S) provenance. This confirms that a source was found, not that every snippet fact is current or correct.
* `UNVERIFIED`: invalid/placeholder provenance or a candidate that cannot meet the stronger source rules; it is excluded from recommendations.
* `DEMO`: an offline Pathly dataset record, not a live or verified listing.

Unknown external facts—including deadline, funding, eligibility, provider, country, requirements, and delivery mode—remain unknown. Results are upserted by normalized source URL first and title/provider second, so repeated searches do not continually add rows. Users should inspect the linked source before applying.

## 3-Minute Demo

1. Log in with the demo account.
2. View current readiness and backend-derived charts.
3. Open **My Path** and inspect the Experience Gap.
4. Open a recommended research opportunity.
5. Observe Match, Readiness, Gap Impact, explanation, and eligibility.
6. Add it to Roadmap and complete a task.
7. In Profile, enter IELTS `7.0` and save.
8. Return to Dashboard to see the language gap resolve and history update.
9. Ask the AI Advisor what to do next.
10. Review a motivation letter against a seeded scholarship.

## Known MVP limitations

Web search establishes provenance but does not prove that every page is official, current, or complete; therefore the current adapter returns `SOURCE_FOUND`, not `VERIFIED`. Search-result extraction intentionally leaves unavailable structured facts unknown. The offline catalogue supports reliable demonstration but is not live data. Readiness is heuristic progress—not admission probability or a guarantee. Real-provider behavior depends on provider availability. SQLite is intended for demo/development; production should use PostgreSQL, a durable refresh job and a first-party page verification/expiry pipeline.

## Future development

Verified opportunity ingestion, institution integrations, counselor dashboards, notifications/calendar sync, verified requirement extraction, localization, mentor connections, exam pathways, and longitudinal outcome measurement.
