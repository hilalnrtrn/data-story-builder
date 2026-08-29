# ADR-008: Deterministic story safety instead of a second LLM

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

Story structure, source identity, numerical evidence, semantic safety, causality and narrative framing are checked with deterministic application code. A second LLM is not used as the truth auditor.

## Context

An LLM judging another LLM would add cost and latency without making numerical or semantic decisions reproducible. The persisted structured evidence already provides an authoritative comparison target.

## Consequences

- Audit behavior is testable, explainable and independent of provider availability.
- Numerical representation rules and semantic patterns require explicit maintenance and tests.
- Provider failure cannot be masked by an auditor-generated replacement story.

## Alternatives considered

- **Second LLM as semantic/numerical judge:** rejected for nondeterminism, cost and circular trust.
- **No post-generation audit:** rejected because grounded input alone does not guarantee grounded output.
