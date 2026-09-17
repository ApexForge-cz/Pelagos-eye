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

`GET /system/status` returns the application version and database probe result. A missing
or unreachable database produces `DEGRADED`, database `OFFLINE`, and `DATA UNAVAILABLE`.
Database-backed `/data/sources` requests instead return a stable 503
`application/problem+json` response without leaking connection details.

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

## Remaining boundary

The API exposes source metadata and does not bypass record-level redistribution gates.
WPI redistribution remains `unreviewed`; MarineCadastre record redistribution remains
`restricted`. Scheduled ingestion and active provider probes remain separate work.
