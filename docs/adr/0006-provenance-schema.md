# ADR-0006: Source catalog and ingestion provenance foundation

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

Every Phase 2 provider must preserve source identity, version, retrieval and event times,
cache state, quality findings, and reproducibility metadata. Building provider-specific
tables first would duplicate these rules and make outages or invalid records difficult to
audit consistently.

## Decision

Create four shared PostgreSQL tables before integrating a provider:

- `data_source` stores official references, attribution, licensing review, and
  redistribution status.
- `source_version` stores data/schema versions, publication and retrieval times,
  checksums, and artifact references.
- `ingestion_run` stores idempotency keys, controlled run/source states, code revision,
  parameters, timestamps, and accepted/rejected counts.
- `quality_issue` stores controlled quality codes, severity, affected-record counts, and
  bounded diagnostic references.

Use database constraints for controlled states, count invariants, checksum pairing,
source-version ownership, and UTC-capable timestamps. Service logic validates lifecycle
transitions and idempotent reuse. Repositories flush but do not commit; transaction
ownership remains with the calling use case.

Provider records will reference this foundation when their vertical slices are added.
No provider data, production fixture, or public business route is introduced by this
decision.

## Consequences

- Every later provider starts with a consistent, queryable provenance envelope.
- Invalid lifecycle transitions are rejected in the service, while critical invariants
  remain protected by PostgreSQL constraints.
- The first migration is intentionally metadata-only and does not yet exercise PostGIS
  geometry or metric queries.
- Controlled status and quality-code changes require reviewed migrations and contract
  tests rather than ad hoc strings.
- Repository callers must explicitly commit or roll back their transaction.

## Alternatives considered

- Provider-specific provenance columns only: rejected because semantics and outage states
  would drift across modules.
- A schemaless provenance document table: rejected because core identifiers, timestamps,
  states, and counts require relational constraints and efficient queries.
- Database-native enum types: deferred because check constraints are easier to evolve
  during Phase 2 while still enforcing the controlled vocabulary.
