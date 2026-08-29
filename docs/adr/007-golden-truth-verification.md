# ADR-007: Golden Truth controlled scenario for analytical verification

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

A controlled demo scenario and `tests/golden/expected_results.json` define expected analytical and safety behavior for deterministic regression tests.

## Context

Passing compilation does not prove analytical correctness. Known changes, contributions, anomalies, relationships, limitations and forbidden claims provide a stable behavioral oracle.

## Consequences

- Analytics changes can be checked against intended meaning and tolerances.
- Clean and dirty datasets exercise both truth and preparation behavior.
- Golden Truth stays test-only: it is not production storage, frontend data or prompt input.

## Alternatives considered

- **Only unit-test isolated functions:** rejected because cross-stage analytical behavior also matters.
- **Hard-code expected demo results in React or prompts:** rejected because it would contaminate runtime behavior.
