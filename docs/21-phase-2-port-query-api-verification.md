# Phase 2 bounded port-query API verification

- Verification date: 2026-09-17
- Scope: read-only, bounded query of publishable port-reference records
- Endpoint: `GET /ports`
- Public source boundary: UNECE UN/LOCODE only while NGA WPI remains `unreviewed`

## Implemented contract

The endpoint accepts optional text, two-letter country, and coordinate-availability
filters. Results use deterministic ordering, `limit` is restricted to 1–100, and `offset`
is restricted to 0–100,000. The response distinguishes total matching records from the
current page.

Each record includes its provider identifier, record type, name, country, UN/LOCODE,
coordinates where supplied, provider status/update fields, and quality flags. Its
provenance includes source identity and URL, attribution, data/schema versions,
publication, retrieval, ingestion and normalization times, controlled source state, and
cache age where applicable. Raw provider records, checksums, and local artifact references
are not returned.

The repository selects the latest successful or partial ingestion run for each source and
applies `redistribution_status = allowed` before counting or returning records. WPI records
remain stored for internal use but cannot cross this public query boundary until the
documented terms review changes their source status.

## Verification evidence

- Ruff formatting and lint checks: passed
- strict mypy check: passed
- focused port-query unit/contract tests: 4 passed
- Linux/PostGIS migration and integration test: passed
- integration fixture imported both `allowed` and `unreviewed` TEST DATA sources; only the
  allowed record was returned
- read-only smoke query against the existing real imports found three `Shanghai` matches,
  all from `unece-unlocode` and none from WPI
- the deployed query uses the same computed source state as `/data/sources`; data outside
  the approved freshness window returns `503 application/problem+json`
- API production image build: passed

## Remaining boundary

This slice does not implement WPI publication, entity resolution, port detail views,
spatial-radius search, or map rendering. Restricted historical AIS records remain
internal rather than receiving a public query endpoint.
