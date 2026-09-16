# ADR-0004: Local infrastructure and initial deployment posture

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

Phase 1 needs a reproducible development topology without claiming a production design or
creating domain schema before real-data work.

## Decision

Use Docker Compose for a local PostGIS, Redis, API, and static web shell. Require local
database credentials through ignored environment files; do not commit default passwords.
Create an empty Alembic baseline so migration commands and CI can evolve without inventing
business tables.

The first public demo, if approved later, targets one Linux container host. Managed data
services and additional workers require measured durability, performance, or cost evidence.

## Consequences

- The topology is reproducible but needs Docker and explicit local credentials.
- Phase 2 can add schema through reviewed migrations.
- Compose images and deployment costs require periodic review.

## Alternatives considered

- Installing PostgreSQL and Redis directly on every host: rejected as the documented path.
- Kubernetes: rejected as unjustified for a single-developer first release.
