# ADR-006: Separate facts, insights, and hypotheses

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

Facts, derived insights and possible explanations remain distinct. Hypotheses are deterministic entities with source links, confidence, evidence, counter-evidence, missing context and explicit lifecycle state.

## Context

Mixing speculative explanation with verified findings would misrepresent epistemic certainty and could cause story wording to overwrite analytical truth.

## Consequences

- Hypothesis states are `OPEN`, `SUPPORTED`, `CONFIRMED` and `REJECTED`.
- Backend transitions are constrained and their reasons persisted.
- Updating a hypothesis never rewrites its source facts or insights.
- The LLM does not discover hypotheses.

## Alternatives considered

- **Embed possible explanations directly in insights:** rejected because speculation would appear factual.
- **Let generated prose create hypotheses:** rejected because candidates and confidence would become non-deterministic.
