# Data Story Builder

Data Story Builder is an explainable analytics and executive-storytelling research prototype built during a 20-business-day software engineering internship. It turns structured CSV or Excel data into validated findings, relationships, hypotheses, and an auditable executive narrative without treating an LLM as an analytics engine.

**Product flow:** Data → Analyze → Question → Verify → Plan → Narrate → Audit → Explain

## Contents

- [Project purpose](#project-purpose)
- [Architecture](#architecture)
- [Detailed architecture](docs/architecture.md)
- [Architecture decision records](docs/adr/README.md)
- [LLM boundary](#llm-boundary)
- [Fact, insight, and hypothesis](#fact-insight-and-hypothesis)
- [Technology stack](#technology-stack)
- [Repository structure](#repository-structure)
- [Setup](#setup)
- [Run the application](#run-the-application)
- [Database and persistence](#database-and-persistence)
- [API](#api)
- [Analytics and explainability](#analytics-and-explainability)
- [Story safety](#story-safety)
- [Golden Truth and demo data](#golden-truth-and-demo-data)
- [Testing](#testing)
- [Frontend capabilities](#frontend-capabilities)
- [MVP limitations](#mvp-limitations)
- [Security and secrets](#security-and-secrets)
- [Internship context](#internship-context)

## Project purpose

The application accepts structured business data, prepares and profiles it, discovers explainable findings, evaluates their integrity and business relevance, and creates an executive story whose claims remain traceable to deterministic evidence.

It is not a generic chatbot and does not send raw datasets to an LLM for analysis. Users can inspect what happened, why a finding matters, which evidence supports it, what contradicts it, and where the available data cannot establish causality.

## Architecture

```text
User Excel/CSV
→ React UI
→ ASP.NET Core Web API
→ Data Ingestion / Preparation
→ Data Profiler
→ Metric/Data Integrity
→ Insight Engine
→ Relationship Engine
→ Business Relevance
→ Insight Integrity
→ Causality Guard
→ Missing Context
→ Story Planner
→ LLM
→ Story Generator
→ Story Auditor
→ Executive Story
→ Hypothesis Tracker
→ PostgreSQL
```

Python performs data preparation and deterministic/statistical analysis. ASP.NET Core orchestrates the workflow, story planning and generation, auditing, read contracts, and persistence. React presents persisted results and does not recompute analytics.

## LLM boundary

The LLM is **not** the analytics engine. It receives bounded, validated story-planner input rather than raw CSV or Excel rows.

The LLM must not:

- calculate business metrics or discover findings from raw data;
- invent evidence, confidence, importance, or unsupported causal claims;
- present missing competitor, pricing, campaign, or operational context as fact;
- change source identifiers, numerical meaning, or planner-supplied story structure.

The Story Planner runs before generation and story audits run afterward. The configured provider is accessed through the backend LLM abstraction. A provider call occurs only during deliberate new-analysis submission—not while opening persisted results, switching sections, changing UI language, refreshing, or using History.

## Fact, insight, and hypothesis

| Concept | Meaning |
| --- | --- |
| Fact | A statement directly verifiable from the dataset. |
| Insight | An analytical finding derived from facts through deterministic or statistical logic. |
| Hypothesis | A possible explanation supported by evidence but not proven by available data. |

Hypotheses remain separate from facts and insights. Their states are `OPEN`, `SUPPORTED`, `CONFIRMED`, and `REJECTED`, with supporting evidence, counter-evidence, and missing context preserved where available.

## Technology stack

- **Frontend:** React 19, Vite 8, Chart.js 4, react-chartjs-2
- **Backend:** ASP.NET Core Web API on .NET 8, Entity Framework Core
- **Analytics:** Python, FastAPI, pandas, NumPy
- **Database:** PostgreSQL
- **Story provider:** OpenAI-compatible provider through the backend abstraction (currently Groq)
- **Tests:** pytest, xUnit, ESLint, Vite production build

## Repository structure

```text
data-story-builder/
├── analytics/                         Python/FastAPI analytics service and tests
├── backend/
│   ├── DataStoryBuilder.Api/          endpoints and composition root
│   ├── DataStoryBuilder.Application/  orchestration, story, audit, read logic
│   ├── DataStoryBuilder.Domain/       domain models and contracts
│   ├── DataStoryBuilder.Infrastructure/ PostgreSQL/external-service adapters
│   └── DataStoryBuilder.Application.Tests/ .NET tests
├── database/                          database resources
├── docs/                              dictionary, scenario, expected insights
├── frontend/                          React application
├── sample-data/                       controlled clean, dirty, Excel datasets
├── scripts/                           repository helpers
├── tests/golden/                      Golden Truth expectations
└── DataStoryBuilder.sln
```

## Setup

### Prerequisites

- Git, .NET 8 SDK, and Entity Framework Core CLI (`dotnet-ef`)
- Python with virtual-environment support
- Node.js and npm
- PostgreSQL
- An approved provider key only for deliberate fresh story generation

Commands use Windows PowerShell from the repository root unless noted.

### Install dependencies

```powershell
git clone <repository-url>
Set-Location data-story-builder

python -m venv analytics\.venv
analytics\.venv\Scripts\Activate.ps1
python -m pip install -r analytics\requirements.txt

npm.cmd --prefix frontend install
```

### Configure secrets

Committed configuration contains non-secret defaults. Store local credentials outside source control:

```powershell
dotnet user-secrets set "ConnectionStrings:PostgreSqlPassword" "<postgres-password>" --project backend\DataStoryBuilder.Api
dotnet user-secrets set "Llm:ApiKey" "<provider-api-key>" --project backend\DataStoryBuilder.Api
```

The default PostgreSQL target is `localhost:5432`, database `data_story_builder`, user `postgres`. Override other settings through user secrets or environment-specific configuration when needed.

### Apply existing migrations

With PostgreSQL running and the target database available:

```powershell
dotnet ef database update --project backend\DataStoryBuilder.Infrastructure --startup-project backend\DataStoryBuilder.Api
```

This applies existing migrations for analyses, structured/generated stories, audits, hypotheses, and story-generation language metadata.

For a frontend API override, copy `frontend/.env.example` to ignored `frontend/.env.local`; never commit machine-specific values.

## Run the application

Open three PowerShell terminals.

### Analytics service

```powershell
Set-Location analytics
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Health: `http://127.0.0.1:8000/health`

### ASP.NET Core API

```powershell
dotnet run --project backend\DataStoryBuilder.Api --launch-profile http
```

API: `http://localhost:5056`

Health: `http://localhost:5056/api/health`

Swagger (Development): `http://localhost:5056/swagger`

### React frontend

```powershell
npm.cmd --prefix frontend run dev
```

Frontend: `http://localhost:5173`

## Database and persistence

PostgreSQL is the source of truth for completed analyses and historical reopening. The persisted result package includes analysis metadata, preparation/profile results, insights, relationships, integrity and relevance outputs, structured and generated stories, story audits, hypotheses, and generation-language metadata.

Uploaded business rows pass through ingestion and analytics; the application persists the analytical result package rather than creating a frontend-owned analytical copy. History uses a lightweight persisted list contract, then loads complete detail for the selected analysis.

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | API health check |
| `POST` | `/api/analyses` | Submit a CSV/Excel `file` and optional multipart `language` |
| `GET` | `/api/analyses` | List persisted summaries for History |
| `GET` | `/api/analyses/{id}` | Load a complete persisted analysis read model |
| `GET` | `/api/analyses/{analysisId}/hypotheses` | Read persisted hypotheses |
| `PATCH` | `/api/analyses/{analysisId}/hypotheses/{hypothesisId}/status` | Change hypothesis state |

Example deliberate submission:

```powershell
curl.exe -X POST "http://localhost:5056/api/analyses" `
  -F "file=@sample-data/sales_demo_clean.csv" `
  -F "language=tr"
```

Submission runs the full pipeline and can consume provider quota. Refresh and History restoration use `GET` only. The analytics service separately exposes `GET /health` and backend-facing `POST /datasets/prepare`.

## Analytics and explainability

The Insight Engine produces explainable `CHANGE`, `TREND`, `ANOMALY`, `CONTRIBUTION`, and `CONTRAST` findings. Confidence and importance remain distinct. The wider pipeline adds:

- relationships and business relevance;
- calculations and evidence;
- counter-evidence, contradiction, outlier, one-off, and consistency checks;
- causality status and causal-language safeguards;
- missing-context limitations.

The **Why This Insight?** workspace presents these persisted results without moving calculation into React.

## Story safety

Generation uses a structured plan with source-item identifiers and bounded evidence. Post-generation safeguards include:

- Story/Data Diff and numerical-evidence matching;
- source-item and claim/evidence traceability;
- evidence coverage and unsupported-claim checks;
- causal-overstatement checks;
- narrative-framing and bias checks;
- preservation of qualifications, counter-signals, and missing context.

Generation language is selected at new-analysis time and persisted. Changing frontend language does not translate or regenerate historical prose, preventing hidden provider calls and preserving the original artifact.

## Golden Truth and demo data

The controlled scenario is the project's test laboratory:

- `sample-data/sales_demo_clean.csv`
- `sample-data/sales_demo_dirty.csv`
- `sample-data/sales_demo.xlsx`
- `tests/golden/expected_results.json`

Golden Truth verifies metric changes, contributions, anomaly discovery, relationship wording, causal restraint, missing context, and dirty-data preparation. It is a test oracle—not a source of hard-coded production UI values.

See `docs/data_dictionary.md`, `docs/demo_scenario.md`, and `docs/expected_insights.md` for the controlled scenario.

## Testing

```powershell
# Python analytics
analytics\.venv\Scripts\python.exe -m pytest analytics

# Complete .NET solution
dotnet test DataStoryBuilder.sln

# Frontend
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build

# Whitespace integrity
git diff --check
```

If a running API locks Debug assemblies on Windows, stop only that API process, test, and restart it with the same profile.

The latest completed full-regression checkpoint passed **1,254 Python tests** and **394 .NET tests**, plus frontend lint and production build. Totals may grow; a passing current run is authoritative.

## Frontend capabilities

- CSV/Excel upload and truthful analysis state
- persisted current-analysis restoration with `GET` only
- Overview KPIs and charts; Dataset Health and preparation detail
- Insight Explorer and **Why This Insight?** explainability
- Executive Story with claim/evidence traceability
- Story Audit and narrative-bias presentation
- hypothesis review and status controls
- persisted History and safe switching
- Turkish/English UI, responsive layouts, light/dark themes

React remains presentation-only: analytical values originate in backend read models, and navigation never triggers generation.

## MVP limitations

This is a research prototype, not a production multi-tenant platform. Deliberate limits include:

- controlled structured CSV/Excel input rather than arbitrary enterprise data;
- no enterprise authentication or multi-user authorization;
- no ERP, Teams, Outlook, Power BI, or streaming integration;
- no advanced causal inference—association is not causation;
- no automatic translation of persisted generated stories;
- provider availability/quota required for fresh story generation;
- primary analytical validation against the controlled scenario and Golden Truth.

## Security and secrets

- Never commit provider keys, database passwords, connection secrets, or local `.env` files.
- Use .NET user secrets or environment-specific secret management.
- Keep `frontend/.env.local`, credentials, logs, and runtime artifacts out of Git.
- Do not place secrets in commands, screenshots, issues, or fixtures.
- Treat uploaded business data and persisted analytical results as sensitive.

## Internship context

Data Story Builder was developed as a focused 20-business-day, approximately 100–120-hour internship MVP. It prioritizes a complete explainable vertical slice: deterministic analytics, evidence-linked storytelling, explicit uncertainty, post-generation auditing, persistence, and a professional bilingual frontend.

The project demonstrates that an LLM can be constrained to narrative composition while analytical truth remains owned by deterministic/statistical code and audited persisted evidence.
