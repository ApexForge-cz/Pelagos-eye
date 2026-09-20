# Phase 4 Live AIS contract kickoff

**Status:** Contract proposal only. Phase 4 remains `Planned` and no live AIS capability is
authorized or claimed by this document.

**Date:** 2026-09-19

## Purpose

Freeze the smallest provider-neutral client contract needed for Developer A and Developer B
to review Phase 4 without starting provider integration. The contract makes freshness,
coverage, availability, reconnects, gaps, and nullable AIS observations visible before any UI,
gateway, worker, storage, or migration work begins.

## Scope of this kickoff

Included:

- typed Python and TypeScript shapes for normalized live vessel positions;
- versioned snapshot, position, status, and gap events;
- WGS 84 bounds, provenance, UTC-aware event/ingest/normalize/emit times, and quality flags;
- separate connection, source, availability, and coverage vocabularies;
- explicit epoch/sequence and no-replay semantics; and
- contract validation tests that reject sentinel values, impossible cache claims, unavailable
  payloads with records, replay claims, and unknown fields.

Excluded:

- AISStream account use, provider code, live network calls, secrets, and raw message fixtures;
- FastAPI routes, WebSocket handlers, Redis/PostGIS changes, Alembic migrations, and retention;
- vessel search, recent tracks, map layers, detail panels, follow mode, or production UI;
- test vessel generation outside test-only contract payloads; and
- any claim of global, continuous, complete, or production live AIS coverage.

## Contract summary

| Concern | v1 contract |
| --- | --- |
| Version | Every event carries `protocol_version = "1.0"`. |
| Event kinds | `vessel.snapshot`, `vessel.position`, `stream.status`, `stream.gap`. |
| Continuity | `stream_epoch` plus a monotonic `sequence`; a new epoch or gap requires a snapshot. |
| Replay | `replay_available` is always `false`; v1 sequence values are not replay offsets. |
| Times | Observation, ingestion, normalization, and emission times are distinct and timezone-aware. |
| Units | WGS 84 degrees, speed in knots, course/heading in degrees. |
| Missing AIS values | Provider sentinels become `null`; no zero or inferred identity fallback. |
| Provenance | Source reference, attribution, data/schema version, provider message type, timestamps, state, cache age, and quality flags. |
| Availability | `AVAILABLE` and `DATA UNAVAILABLE`. |
| Source state | `LIVE`, `CACHED`, `DELAYED`, and `OFFLINE`. |
| Coverage | `COVERED` with explicit bounds, or `NO COVERAGE`; this is not a source state. |
| Connection | `CONNECTING`, `CONNECTED`, `RECONNECTING`, or `DISCONNECTED`; this is not a freshness claim. |

An available snapshot with zero positions means no matching observations were returned for the
declared covered window. `NO COVERAGE` means the source does not cover the requested scope.
`DATA UNAVAILABLE` means the system cannot provide usable records. The UI must not merge these
three cases.

## Ownership and integration boundary

Developer A owns the public contract, frontend adapter, vessel/map experience, connection and
coverage presentation, accessibility, and integration acceptance. Developer B retains the
AISStream adapter, worker supervision, validation/normalization/deduplication, Redis/PostGIS,
recent-track/search backend, gateway backpressure, health telemetry, and provider/backend
tests. Existing stable modules do not move.

The public contract is provider-neutral. Developer B may propose source-specific additions,
but raw provider dictionaries do not enter API routes or frontend types. Contract changes are
reviewed before either side implements against them. Only Developer A creates or approves a
resulting Alembic migration.

## Entry gates for implementation

Phase 4 implementation must not begin until the owner records and approves all of the following:

1. Current AISStream documentation and applicable terms are reverified, including public
   display, caching, retention, redistribution, connection limits, and attribution.
2. A server-only account/key path is available and secret-scanning controls are confirmed.
3. The first demo geography, subscription bounds, message types, and coverage wording are set.
4. Raw and normalized retention, storage budget, deletion behavior, and migration owner are set.
5. Reconnect/backoff, queue limits, coalescing, slow-client behavior, and gap metrics are set.
6. Developer A and B issue scopes, allowed paths, review order, and acceptance evidence are set.

## Proposed implementation order after authorization

1. Developer B verifies the provider and submits a source/terms record plus a contract mapping.
2. The shared contract is accepted or revised; the cross-language fixtures remain authoritative.
3. Developer B implements bounded ingestion and failure behavior behind the adapter boundary.
4. Developer B implements latest state, persistence, gateway, and backend/load tests.
5. Developer A integrates snapshot/status/gap handling before rendering live positions.
6. Developer A adds vessel layer/search/detail/follow with freshness and coverage beside values.
7. Both owners run disconnect, burst, stale-cache, no-coverage, and unavailable acceptance tests.

## Kickoff acceptance evidence

- Python validation and frontend type checks pass without registering a route or provider.
- The contract rejects raw extra fields and does not contain credentials.
- Tests show AIS unavailable sentinels are `null`, cache age matches `CACHED`, and v1 cannot
  claim replay.
- README and risk documentation continue to mark live AIS as planned.
- Format, lint, type checks, focused tests, build, `git diff --check`, and secret checks pass.

## Open decisions

- Demo region and maximum subscription extent.
- Provider terms/rights evidence date and approved public-display wording.
- Raw/normalized retention and whether raw storage is permitted at all.
- Snapshot limits, update coalescing interval, queue sizes, and latency/error budgets.
- REST snapshot/search paths, WebSocket path, authentication, origin policy, and quotas.
- Static identity/voyage observation shape, including independent observation time,
  provenance, conflict handling, and nullable provider sentinels.
- Whether a later durable replay capability belongs in Phase 4 or remains historical analytics.
