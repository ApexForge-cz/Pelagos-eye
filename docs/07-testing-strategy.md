# Testing Strategy

## Goals

Testing must protect data truth, spatial/temporal correctness, provider resilience, and
core user workflows. The suite should be layered so either developer can get fast feedback
locally while shared CI/release jobs provide deeper assurance.

## Test pyramid

| Layer | Purpose | Examples |
| --- | --- | --- |
| Static | reject common defects cheaply | Ruff, mypy, strict TypeScript, ESLint, format checks, secret scan |
| Unit | verify pure rules and transforms | coordinate/time/unit parsing, freshness state, angle differences, anomaly thresholds |
| Property/invariant | explore broad input space | valid ranges, idempotent normalization, ordering, geometry round trips |
| Contract | detect provider/schema drift | recorded sanitized payloads against adapters and response schemas |
| Integration | verify storage/cache/provider boundaries | PostGIS queries, migrations, repository transactions, Redis degradation |
| Component | verify accessible UI states | loading/empty/live/cached/delayed/offline, filters, tables, inspectors |
| End-to-end | protect critical workflows | find port/vessel, inspect provenance, replay history, provider outage behavior |
| Performance | enforce budgets | ingestion throughput, spatial query p95, WebSocket fan-out, map frame/memory |
| Resilience/security | exercise failures and abuse | disconnect/reconnect, malformed frames, slow clients, rate limits, injection |

## Test data policy

- Fixtures live under test-only paths and are labeled `TEST DATA` in metadata.
- Prefer small, sanitized, terms-compatible samples representing real schemas.
- Synthetic records may be used for boundary/property/load tests but are labeled `SYNTHETIC BENCHMARK` and cannot enter production stores.
- Production configuration must not import fixture packages or expose fixture endpoints.
- Golden analytical outputs include input checksum, algorithm version, units, and tolerance.

## Domain-critical cases

### Time

- UTC conversion, explicit offsets, leap day, daylight-saving display boundaries, out-of-order and late events, provider future timestamps, stale thresholds.

### Geography

- longitude/latitude ordering, boundary values, antimeridian crossing, polar coordinates, invalid geometries, point-in-polygon edges, metric operations using appropriate CRS/geography.

### AIS

- Missing/static fields, sentinel values, malformed MMSI, duplicate frames, inconsistent identity, zero/stationary speed, course wraparound, observation gaps, burst/backpressure and reconnect.

### Port resolution

- Same names in different countries, one source missing identifiers, conflicting coordinates, non-port UN/LOCODE entries, superseded codes.

### Analytics/anomalies

- Denominator and bucket boundaries, empty windows, sampling disclosure, deterministic rerun, dwell at boundary, course difference across 359°/0°, missing-coverage suppression.

## Provider contract testing

- Store sanitized canonical examples and error responses with capture date/source version.
- Parse unknown additive fields safely and fail clearly on breaking envelope changes.
- Run opt-in live smoke tests with secrets only in protected environments; ordinary CI must not depend on public-provider availability.
- Alert on schema drift before accepting new fields/semantics.

## Database and migrations

- Apply every migration from empty database and from the previous supported release.
- Test constraints, indexes, SRIDs, query plans for reference workloads, and idempotent ingestion.
- Verify backup/restore and migration rollback/recovery path before releases.
- Use ephemeral PostgreSQL/PostGIS in CI; SQLite is not a substitute for spatial behavior.

## Frontend testing

- Component tests cover all data states, accessible names, keyboard flow, reduced motion, unit labels, and attribution.
- Visual regression uses stable fixtures and masks only truly nondeterministic rendering.
- Browser E2E covers current supported Chromium, Firefox, and WebKit policy selected in Phase 1.
- WebGL capability tests verify fallback UI; avoid pixel-perfect assertions for unstable map tiles.

## Performance plan

Phase 1 defines budgets; Phase 2–5 establish measured baselines. Required scenarios include:

- sustained and burst AIS message ingestion
- WebSocket delivery with slow/disconnected clients
- bounded spatial/time query on representative partitions
- historical import memory/disk profile
- map pan/zoom/select with representative visible feature counts
- long playback session and tab background/restore

Record hardware, dataset checksum, configuration, percentile distribution, peak memory, and pass/fail threshold.

## CI lanes

- **Pull request:** formatting, lint, type checks, unit, contract, component, migration smoke, secret/dependency checks.
- **Main/nightly:** full integration, browser E2E, selected live-provider smoke, larger spatial/performance regression.
- **Release:** full suite, container/SBOM scan, accessibility audit, representative load/soak, backup restore, deployment smoke.

No test is silently skipped in a required lane. Conditional tests report why they did not run.

## Quality gates

- All required checks pass.
- New important business logic has positive, negative, boundary, and failure tests.
- No critical/high security result remains unresolved.
- Coverage is used diagnostically; changed critical modules require meaningful behavioral coverage, not a vanity global percentage.
- Performance regressions beyond agreed tolerance require investigation or explicit recorded acceptance.
- Data fixtures and snapshots are reviewed for secrets, personal data, and redistribution rights.

## Defect handling

Every production data-integrity defect receives a regression test and assessment of affected derived outputs. Corrected results get a new data/algorithm version; old published results are marked superseded rather than invisibly rewritten where reproducibility matters.
