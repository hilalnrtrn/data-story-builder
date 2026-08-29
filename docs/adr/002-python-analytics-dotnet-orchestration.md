# ADR-002: Python analytics and ASP.NET Core orchestration split

- **Status:** Accepted
- **Context:** 2026 internship MVP

## Decision

Python/FastAPI owns preparation, profiling and deterministic/statistical analytics. ASP.NET Core owns the public API, application lifecycle, persistence coordination, grounded generation, auditing integration and hypothesis lifecycle endpoint.

## Context

Python provides mature tabular/statistical tooling, while .NET provides the established application and persistence boundary. The split keeps analytical code close to pandas/NumPy and the product lifecycle close to ASP.NET Core/EF Core.

## Consequences

- The services exchange a structured analytics contract over HTTP.
- Availability and contract failures are explicit boundaries.
- Each test suite can validate its responsibility independently.

## Alternatives considered

- **Rewrite everything in C#:** rejected as unnecessary risk within the internship schedule.
- **Move orchestration and persistence into Python:** rejected because it would duplicate or replace the established .NET application boundary.
- **Expand to many microservices:** rejected as out of MVP scope.
