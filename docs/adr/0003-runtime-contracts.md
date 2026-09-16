# ADR-0003: Configuration, logging, health, and errors

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

Every later provider and data feature needs consistent configuration, diagnostics, and
failure behavior. Establishing these contracts after integrations would produce drift.

## Decision

- Load server settings through typed Pydantic settings using `OCEANSCOPE_` variables;
  provider secrets use server-only names and `SecretStr`.
- Emit human-readable structured logs in development and JSON logs outside development.
- Add or propagate `X-Correlation-ID` and never log query strings or secret values.
- Expose `/health/live` and `/health/ready`; Phase 1 readiness means the API process and
  configuration loaded, not that future external providers are healthy.
- Return validation failures as `application/problem+json` with a stable shape.

## Consequences

- Later modules inherit one operational vocabulary.
- Readiness must be extended when PostgreSQL, Redis, and providers become required.
- Error types use placeholder documentation URIs until a public base URL exists.

## Alternatives considered

- Ad hoc environment reads and standard text logs: rejected because they make validation,
  testing, and correlation inconsistent.
