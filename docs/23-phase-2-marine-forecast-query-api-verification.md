# Phase 2 bounded marine-forecast query API verification

- Verification date: 2026-09-18
- Scope: read-only query of stored Open-Meteo marine forecast points
- Endpoint: `GET /ocean/forecast`

## Implemented contract

Every request supplies the original requested WGS 84 coordinate and an offset-aware time
window no longer than seven days. Pagination is capped at 168 hourly rows. The repository
selects the most recent successful or partial ingestion run matching the coordinate within
six decimal places, preventing older forecast snapshots from being mixed into the result.

Each point includes requested and selected model-grid coordinates, UTC valid time, model
routing label, seven typed forecast variables, provider units, quality flags, source state,
data/schema version, attribution, retrieval, ingestion, and normalization time. Raw JSON
records and local artifact references are not returned. The response identifies the data
as a model forecast and excludes navigation, collision avoidance, and emergency use.

## Verification evidence

- Ruff formatting and lint checks: passed
- strict mypy check: passed
- focused query contract, validation, and freshness tests: 7 passed
- Linux/PostGIS migration and query integration test: passed
- integration query returned the expected wave value and Open-Meteo provenance
- local Compose API health and readiness probes returned HTTP 200
- a real stored-data query for `20,-40` returned 24 hourly records from
  `open-meteo-marine`, covering `2026-09-17T13:00:00Z` through
  `2026-09-18T12:00:00Z`
- the real response preserved the requested coordinate (`20,-40`) and selected model-grid
  coordinate (`20.041664,-40.041656`), units, source version, timestamps, source state,
  attribution, and model-use warning
- an eight-day query window returned HTTP 422 with `application/problem+json` and the
  bounded-window error detail
- after the freshness policy deployment, the same real query still returned 24 `LIVE`
  records while the source remained inside its six-hour freshness objective

## Remaining boundary

Only coordinates previously imported by the internal bounded importer are queryable. The
endpoint does not fetch on demand, interpolate between points, claim one underlying model
for `best_match`, or refresh on demand. Scheduled refresh, dense grids, map tiles, and
navigation use remain unfinished or out of scope.
