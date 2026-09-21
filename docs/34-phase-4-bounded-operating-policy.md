# Phase 4 bounded Live AIS operating policy

**Status:** Owner-approved revised planning boundary. Implementation remains blocked on
self-service credential evidence and an issue-scoped Phase 4 authorization.

**Date:** 2026-09-20; provider/scope revision 2026-09-22

**Original policy issue:** [#30](https://github.com/ApexForge-cz/Pelagos-eye/issues/30)

**Revised provider gate:** [#37](https://github.com/ApexForge-cz/Pelagos-eye/issues/37)

## Decision

The first Live AIS slice is restricted to one fixed Gulf of Finland subscription and
Pelyr `/v1` position frames only. It uses one centralized backend provider connection,
keeps no raw messages, stores no track tails, and writes no live AIS data to Redis,
PostGIS, files, backups, or analytics storage.

The reviewed Pelyr terms permit bounded in-product display and in-memory handling when
source-specific attribution and anti-extraction restrictions are enforced. This policy does
not authorize a connection by itself: a self-service key, key-backed `/v1` welcome/source
directory/coverage smoke check, and an implementation issue approved by Developer A are
still required. AISStream issue #298 remains historical follow-up, not a Phase 4 dependency.

## Fixed subscription

| Item | Approved first-slice value |
| --- | --- |
| Region | Gulf of Finland pilot box |
| CRS | WGS 84 (`EPSG:4326`) at the application boundary |
| West | `23.50` |
| South | `59.50` |
| East | `26.50` |
| North | `60.50` |
| Provider selection | Pelyr `/v1`, `fields = "position"` only |
| Provider connections | One authenticated backend connection |
| Subscription changes | Disabled for the first slice |
| Browser provider access | Prohibited |
| Product data export/API | Prohibited; same-origin UI transport only |

The box is the configured subscription extent, not proof of receiver coverage, complete
vessel reporting, or global availability. Inside the configured and active subscription,
the client contract may report `COVERED`; outside it, the first slice reports
`NO COVERAGE`. An empty covered snapshot means no matching observations were available,
not that no vessels exist. Provider failure remains `DATA UNAVAILABLE` or an explicitly
age-labeled cache within the approved window.

Pelyr `/v1` already uses named west/south/east/north fields. The public contract and
spatial checks retain the same WGS 84 representation. The box is selected because Pelyr
declares Fintraffic as an upstream source; it becomes `COVERED` only after the key-backed
check confirms effective access and current observations or provider coverage evidence.

## Retention and deletion

| Data class | First-slice policy |
| --- | --- |
| Provider credentials | Server-only secret storage; never logged, emitted, committed, or sent to browsers |
| Raw provider frames/messages | Validate and normalize in memory, then discard; zero persistence and zero raw-payload logging |
| Rejected raw messages | Count by reason without retaining the payload |
| Normalized latest position | Memory only, keyed by MMSI, hard expiry after 5 minutes |
| Recent track tail | Disabled; zero retention |
| Durable replay | Unavailable |
| Redis/PostGIS/files/backups | Zero live AIS records in the first slice |
| Process shutdown | Purge all in-memory latest positions and queues |

The persistent live AIS storage budget is therefore zero bytes. Pelyr Data Licence 1.1
permits storage, but the first slice deliberately retains the more conservative
zero-persistence boundary. Source licence ids and attribution remain attached to every
in-memory observation and are discarded with it.

No migration is authorized. A future retention or track feature requires a separate
terms review, data model, storage budget, deletion test, migration review, and issue.

## Initial operating budgets

These are conservative acceptance ceilings for the first implementation proposal, not
claims of measured capacity:

| Resource | Initial ceiling | Required behavior at the ceiling |
| --- | --- | --- |
| Normalized ingress queue | 2,048 position events | Record overflow, emit a server-backpressure gap, and require a fresh snapshot |
| Latest-position state | 10,000 MMSI records | Mark snapshots truncated, raise health degradation, and narrow/stop the slice; do not silently claim completeness |
| Snapshot payload | 5,000 positions | Set `truncated = true`; surface the limitation beside counts and coverage |
| Per-client outbound queue | 256 events | Clear obsolete position events, emit a client-backpressure gap, then send a fresh snapshot |
| Connected demo clients | 25 | Reject excess clients explicitly; do not create another provider connection |
| Same-MMSI delivery coalescing | At most 250 ms | Latest position wins; increment a coalescing metric |
| Live AIS module memory | 128 MiB target ceiling | Fail the load gate and reduce scope/budgets before release |

Load tests must measure actual message size, vessel count, burst rate, queue high-water
marks, coalescing, drops, latency, CPU, and memory before these ceilings can be accepted.
No capacity or completeness claim follows from the proposed numbers.

## Continuity and recovery

- Validate the unprompted Pelyr `welcome` frame, its source directory and effective limits,
  then submit the one fixed subscription within the advertised deadline (currently five seconds).
- Read continuously and consume each 20-second heartbeat. A nonzero provider loss counter,
  unknown licence id, or missing heartbeat is a continuity incident, not silent throttling.
- Reconnect with capped exponential backoff using base delays of 1, 2, 4, 8, 16, and
  30 seconds plus bounded jitter. Reset the attempt count only after 60 seconds of stable
  connectivity.
- Publish `CONNECTING`, `CONNECTED`, `RECONNECTING`, or `DISCONNECTED` independently of
  source freshness, availability, and coverage.
- A provider reconnect or changed source directory creates a new `stream_epoch`. Every provider, server-queue,
  client-queue, or subscription continuity break emits `stream.gap` with
  `replay_available = false` and requires a new snapshot.
- Planned same-MMSI coalescing happens before public sequence assignment and is counted.
  Queue overflow after assignment is a gap, never an invisible skipped sequence.
- If a slow client cannot accept the gap and replacement snapshot, disconnect it. A later
  client reconnect begins with a snapshot; no replay is promised.
- Never interpolate positions across a gap or infer vessel absence from silence.

## Required telemetry

The future implementation must expose bounded-cardinality metrics for connection state,
reconnect attempts, messages received/accepted/rejected, last observation time, queue
depth/high-water mark, coalesced and dropped updates, gaps by reason, snapshot size and
truncation, connected clients, and slow-client disconnects. Metrics and logs must not use
MMSI, coordinates, raw payloads, credentials, or full provider frames as labels or values.

## Ownership and implementation gate

Developer B retains provider and licence mapping, connection supervision, normalization,
latest-state handling, fan-out, telemetry, load tests, and backend failure tests. Developer A
retains the public contract, source/coverage/attribution presentation, frontend state handling,
same-origin anti-extraction boundary, map experience, integration acceptance, and final
migration review. This policy does not transfer stable modules or authorize either owner to
implement before the gate is opened.

| Entry gate | Status after this decision |
| --- | --- |
| Current terms and display/cache/retention/attribution rights | **Recorded:** Pelyr API Terms 1.5 and Data Licence 1.1; per-source runtime attribution required |
| Server-only credential path and live smoke check | **Blocked:** self-service key not yet created or verified |
| Geography, bounds, position fields, and coverage wording | **Approved for planning; live coverage evidence pending** |
| Raw/normalized retention, deletion, and storage budget | **Approved for planning:** zero persistent live-AIS storage |
| Reconnect, queue, coalescing, slow-client, and gap policy | Initial proposal frozen; load evidence still required |
| Same-origin anti-extraction and dynamic attribution behavior | **Approved for planning; implementation tests pending** |
| Implementation issues and owner reviews | Not opened; create only after the credential smoke gate passes |

Phase 4 remains `Planned`. No live AIS capability is implemented or claimed.
