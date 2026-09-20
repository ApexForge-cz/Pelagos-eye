# Phase 2 source and system status API verification

- Verification date: 2026-09-17
- Scope: read-only source catalog/provenance and application dependency status
- Public data records: not exposed

## Contracts

`GET /data/sources` returns a generated timestamp and a bounded list of registered
sources. Each source includes official and terms URLs, attribution, license identifier,
redistribution review state, the controlled `LIVE`/`CACHED`/`DELAYED`/`OFFLINE` state,
availability, latest run, latest usable run/version, counts, and quality findings.

The current run is intentionally separate from the latest usable run. Source state is
computed at request time from the source-specific freshness policy, the usable version's
retrieval time, any initial cache age, and the latest ingestion attempt. If a new provider
attempt fails after an older successful import, the source reports `CACHED` with age only
while that version remains inside the approved stale window. Expired data becomes
`OFFLINE` / `DATA UNAVAILABLE`.

`GET /system/status` returns the application version, PostGIS and Redis probe results,
and a summary for every registered provider. Each provider summary includes its computed
state and availability, freshness thresholds and age, cache age, source publication and
retrieval time, and latest ingestion run with UTC times and record counts. A missing or
unreachable PostGIS or Redis dependency produces `DEGRADED`, dependency `OFFLINE`, and
`DATA UNAVAILABLE`; Redis failure does not create substitute data or prevent the endpoint
from reporting PostGIS-backed provider state. Database-backed `/data/sources` requests
instead return a stable 503 `application/problem+json` response without leaking connection
details.

Provider state is derived from verified stored ingestion evidence and source-specific
freshness policy. It is not an active upstream request on every health check. An empty
provider list with PostGIS `LIVE` means the source catalog is empty; PostGIS `OFFLINE`
means provider status is `DATA UNAVAILABLE`. `NO COVERAGE` is a record-query outcome and
is not used as a health state.

## Evidence

- Ruff format/check: passed
- mypy strict checks: passed for 40 source files
- Linux/PostGIS pytest suite: 38 passed
- Combined test coverage: 83%
- Docker image build: passed
- Real PostGIS API check: passed

The real API check used the official source versions recorded in
`docs/15-phase-2-port-source-verification.md` and returned:

| Endpoint | Result |
| --- | --- |
| `/data/sources` | 200; WPI `LIVE` / `AVAILABLE` / 2,926 accepted; UN/LOCODE `LIVE` / `AVAILABLE` / 17,600 accepted |
| `/system/status` | 200; application `READY`; database `LIVE` |

Automated API tests also cover an unavailable database, a source with no ingestion
history, and a failed latest run with an older usable version. All fixtures are labeled
`TEST DATA` and remain isolated from production configuration.

The original verification predated the explicit freshness policy. The policy extension and
its current validation evidence are recorded in
`docs/24-phase-2-freshness-cache-policy-verification.md`.
Redis and provider/latest-run health hardening is recorded in
`docs/27-phase-2-system-health-hardening-verification.md`.

## Remaining boundary

The API exposes source metadata and does not bypass record-level redistribution gates.
WPI redistribution remains `unreviewed`; MarineCadastre record redistribution remains
`restricted`. Scheduled ingestion and active upstream provider probes remain separate work.
