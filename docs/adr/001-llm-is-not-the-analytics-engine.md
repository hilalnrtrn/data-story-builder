# ADR-001: LLM is not the analytics engine

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

Deterministic, rule-based and statistical analytics own numerical truth, insight discovery, confidence and importance. The LLM only narrates validated structured findings selected by the Story Planner.

## Context

Executive prose benefits from language generation, but raw-data analysis by a provider would weaken reproducibility, grounding and auditability while increasing privacy exposure, cost and hallucination risk.

## Consequences

- Analytical results are repeatable and testable independently of provider wording.
- Provider input is smaller and grounded; output still requires auditing.
- New insight types belong in analytics, not prompts or React.

## Alternatives considered

- **Raw CSV/Excel directly to an LLM:** rejected for weak grounding, privacy exposure and non-reproducible calculations.
- **LLM-generated confidence or importance:** rejected because these values must remain explainable analytical outputs.
