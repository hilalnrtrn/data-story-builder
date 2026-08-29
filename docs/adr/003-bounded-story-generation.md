# ADR-003: Story Planner before LLM and Story Auditor after LLM

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

A deterministic `StructuredStoryPlan` selects permitted findings before generation. .NET projects it into `GroundedStoryPromptInput`; generated structured output is then independently validated and audited.

## Context

Even validated insights can be distorted by free-form selection, unsupported numbers, omitted qualifications, causal wording or invented source references.

## Consequences

- `SourceItemId` provides plan-to-story-to-audit traceability.
- Qualifications, counter-signals, causal constraints and missing context enter the generation contract.
- Failed generation/audits remain explicit and persistable.

## Alternatives considered

- **Free-form prompt containing all insights:** rejected because selection and grounding would be delegated to the LLM.
- **Trust provider JSON without post-validation:** rejected because valid structure does not establish factual support.
