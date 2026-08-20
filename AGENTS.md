# Data Story Builder — Codex Instructions

## Project Purpose

Data Story Builder is a 20-business-day research prototype / MVP developed during a 2026 software engineering internship.

The system analyzes structured Excel/CSV data, discovers important findings and relationships, validates those findings, prioritizes them from a business perspective, and converts validated findings into an explainable and auditable executive data story.

The goal is not to build a generic AI chatbot or a system that sends raw data directly to an LLM.

## Fixed Architecture

Unless explicitly changed by the user, preserve this architecture:

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

Insight Engine includes:

- CHANGE
- TREND
- ANOMALY
- CONTRIBUTION
- CONTRAST
- Confidence
- Importance

Insight Integrity includes:

- Counter Evidence
- Contradiction
- Outlier Check
- One-off Effect
- Data Consistency

Story Auditor includes:

- Story/Data Diff
- Evidence Coverage
- Narrative Bias
- Unsupported claim checks
- Causal overstatement checks

## Technology Stack

Use the following stack unless the user explicitly changes it:

- Frontend: React
- Backend / orchestration: ASP.NET Core Web API / C#
- Analytics: Python + FastAPI + pandas + NumPy
- Database: PostgreSQL
- LLM: OpenAI API or another explicitly approved provider
- Charts: Chart.js or another lightweight approved library
- Development: VS Code + Git + GitHub

Do not introduce unnecessary technologies, frameworks, services, or abstractions.

## Critical LLM Boundary

The LLM is NOT the analytics engine.

The LLM must NOT:

- analyze raw Excel/CSV data
- perform core numerical calculations
- discover insights
- discover relationships
- invent confidence scores
- invent importance scores
- infer unsupported causality
- present information absent from the dataset as fact

Deterministic or statistical analytics code produces numerical facts and validated findings.

The intended flow is:

Validated Structured Findings
→ Story Planner
→ LLM
→ Story Generator
→ Story Auditor

The Story Planner must run before the LLM.

The Story Auditor must run after story generation.

## Fact / Insight / Hypothesis

FACT:
A statement directly verifiable from the dataset.

INSIGHT:
An analytical finding derived from facts.

HYPOTHESIS:
A possible explanation supported by some evidence but not proven by the available data.

Never present a hypothesis as a fact.

Hypothesis states:

- OPEN
- SUPPORTED
- CONFIRMED
- REJECTED

Preserve links to supporting evidence, counter evidence, and missing context.

## Analytics Principles

Prefer explainable, deterministic, rule-based, or statistical methods for the MVP.

Do not replace explainable analytics with opaque AI behavior.

Every important insight should be connected where possible to:

- evidence
- confidence
- importance
- relationships
- business relevance
- integrity results
- causality status
- missing context

The largest percentage change is not automatically the most important business insight.

Correlation or co-movement must not be described as causation without sufficient evidence.

## Golden Truth

The controlled demo dataset is the project's test laboratory.

Expected analytical results must be stored in a Golden Truth structure such as:

tests/golden/expected_results.json

Implementation correctness is not only:

"the code runs"

but also:

"the analytical results match expected behavior."

When relevant, validate analytics against Golden Truth.

## MVP Scope

This is a 20-business-day, approximately 100–120 hour research prototype / MVP.

Do NOT add the following unless explicitly requested:

- Teams integration
- Outlook integration
- Power BI integration
- ERP integration
- streaming architecture
- enterprise authentication
- multi-user architecture
- microservices
- advanced causal AI
- unnecessary Clean Architecture layers
- unnecessary infrastructure
- speculative future features

Prefer the smallest working solution that preserves the fixed architecture.

## Development Workflow

Before making a significant change:

1. Inspect the repository first.
2. Do not immediately modify files.
3. Explain the relevant files and current data flow.
4. Identify risks or ambiguities.
5. Propose a small implementation plan.
6. Wait for user approval when the requested task is exploratory or architectural.

When implementation is requested:

1. Keep the task small.
2. Change only files required for the task.
3. Avoid scope creep.
4. Run the relevant build.
5. Run relevant tests.
6. Validate against Golden Truth when applicable.
7. Review `git diff`.
8. Explain what changed and why.
9. Explain how data flows through the changed code.
10. Report anything incomplete or risky.

Do not mark a task complete merely because code was written.

A task is complete only when reasonably applicable:

- implementation is finished
- build succeeds
- relevant tests pass
- Golden Truth checks pass
- unintended changes are absent
- git diff has been reviewed

## Frontend Boundary

React is a presentation layer.

React must not implement analytical logic.

Frontend responsibilities include:

- file upload
- progress/status
- analysis overview
- charts
- Insight Explorer
- Why This Insight?
- evidence
- integrity results
- Executive Story
- Story Audit
- Hypothesis UI
- analysis history

Analytical values must come from backend/API results.

Do not use hard-coded demo insights in the final application flow.

## Explainability

"Why This Insight?" is a core feature.

When available, preserve or expose:

- What happened?
- Previous value
- Current value
- Absolute change
- Relative change
- Evidence
- Calculation
- Importance
- Confidence
- Relationships
- Business Relevance
- Counter Evidence
- Integrity checks
- Causality status
- Missing Context

## Repository Discipline

Do not:

- commit secrets
- commit API keys
- commit database passwords
- modify unrelated files
- silently change architectural decisions
- add dependencies without a clear reason
- perform large refactors during a small feature task

Use environment variables or local configuration for secrets.

Before finishing a coding task, inspect:

git status
git diff

## Role of Codex

Codex is an implementation agent and pair programmer.

Codex is NOT the architecture authority.

When repository code and these instructions disagree with an explicit newer user decision, follow the user's newer decision.

When uncertain, ask rather than silently redesigning the project.