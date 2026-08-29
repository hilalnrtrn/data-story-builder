# ADR-004: Deterministic Causality Guard

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

Observational association and correlation cannot be narrated as causation unless causality is explicitly established. Deterministic constraints identify allowed and forbidden causal concepts, and semantic audits enforce them.

## Context

Spreadsheet co-movement lacks experimental controls and often lacks competitor, pricing or operational context. `CO_MOVES_WITH` is therefore not a causal edge.

## Consequences

- The controlled MarketingSpend/Revenue relationship remains `CAUSALITY_NOT_ESTABLISHED`.
- Narrative wording can describe association while retaining limitations.
- Missing Context is part of interpretation rather than a fabricated explanation.

## Alternatives considered

- **Automatic causal inference from observational spreadsheets:** rejected as unsupported for this MVP.
- **Allow the LLM to decide causality:** rejected because fluency is not causal evidence.
