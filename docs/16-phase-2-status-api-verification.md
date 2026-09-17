# Phase 2 source and system status API verification

- Verification date: 2026-09-17
- Scope: read-only source catalog/provenance and application dependency status
- Public data records: not exposed

## Contracts

`GET /data/sources` returns a generated timestamp and a bounded list of registered
sources. Each source includes official and terms URLs, attribution, license identifier,
redistribution review state, the controlled `LIVE`/`CACHED`/`DELAYED`/`OFFLINE` state,
availability, latest run, latest usable run/version, counts, and quality findings.

The current run is intentionally separate from the latest usable run. If a new provider
attempt fails after an older successful import, the source reports the current failure as
`OFFLINE` while disclosing that an older traceable version exists. It does not silently
label that version `LIVE` or `CACHED` without an approved cache policy.

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

## Remaining boundary

The API exposes provenance metadata only. It does not return WPI or UN/LOCODE port rows,
perform canonical port matching, establish a cache TTL, or implement the planned frontend
screens. WPI redistribution remains `unreviewed`.
