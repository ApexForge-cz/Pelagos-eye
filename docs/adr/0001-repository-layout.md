# ADR-0001: Repository layout and modular-monolith boundaries

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

OceanScope started with one developer and was expected to contain a web client, API,
ingestion workers, spatial storage, and analytical jobs. Separate repositories or premature
microservices would have increased release and operational work before measured need. The
repository now has two developers, but the same modular-monolith decision remains valid.

## Decision

Use one repository. Place deployable applications under `apps/`, future workers under
`workers/`, infrastructure under `infra/`, cross-platform maintenance commands under
`scripts/`, and durable planning/ADRs under `docs/`. The backend remains a clean-ish
modular monolith with route → service → repository/provider boundaries.

Phase 1 creates only `apps/web` and `apps/api`. Empty abstraction packages are not added
until a real consumer exists.

## Consequences

- One checkout and one CI workflow cover the whole foundation.
- Feature boundaries remain explicit without distributed-system overhead.
- A worker can become independently deployable later without becoming a separate product.
- Repository checks take longer as the project grows and may later need path filtering.

## Alternatives considered

- Separate frontend/backend repositories: rejected because it adds coordination overhead.
- Microservices from the start: rejected because no scaling or ownership evidence exists.
