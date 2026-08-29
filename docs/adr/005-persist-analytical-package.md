# ADR-005: Persist validated analytical packages, not a raw warehouse

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

PostgreSQL persists analysis lifecycle and the validated result package—including evidence, story artifacts, audits and hypotheses—but is not used as a warehouse for every uploaded raw row.

## Context

The MVP requires reliable History, reload and auditability without introducing warehouse ingestion, governance and retention scope.

## Consequences

- History/detail reads use persisted results without recomputation or provider calls.
- Storage and privacy exposure are reduced relative to a raw-row warehouse.
- Re-analysis requires a deliberate new upload rather than replaying stored raw rows.

## Alternatives considered

- **Persist every uploaded row:** rejected due to scope, storage, privacy and governance complexity.
- **Store full results only in the browser:** rejected because PostgreSQL is the source of truth for History and restoration.
