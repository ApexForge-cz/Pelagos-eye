# Phase 2 bounded earthquake-query API verification

- Verification date: 2026-09-18
- Scope: read-only query of stored USGS earthquake events
- Endpoint: `GET /earthquakes`

## Implemented contract

Every request supplies an offset-aware time window and a WGS 84 bounding box. The time
window cannot exceed 31 days, antimeridian-crossing boxes are rejected, pagination is
capped at 100 records per page, and an optional minimum magnitude can further restrict the
result. PostGIS evaluates the spatial intersection.

Each result distinguishes event time, provider update time, source publication and
retrieval times, ingestion completion, and normalization time. It includes coordinates,
depth in kilometres, magnitude, place, provider review status, significance, authoritative
detail link, quality flags, source state, data/schema version, and USGS attribution. Raw
GeoJSON features and local artifact references are not returned. The response explicitly
states that `tsunami` is USGS metadata, not an OceanScope impact prediction or warning.

## Verification evidence

- Ruff formatting and lint checks: passed
- strict mypy check: passed
- focused query contract, validation, and freshness tests: 9 passed
- Linux/PostGIS migration and spatial-query integration test: passed
- integration query matched the expected event by time, WGS 84 box, and minimum magnitude
- deployed real-data smoke query returned four stored events, all attributed to
  `usgs-earthquakes`
- a request exceeding the 31-day window returned HTTP 422 with
  `application/problem+json`
- after the stored feed exceeded its one-hour maximum cache window, the deployed endpoint
  returned HTTP 503 with `application/problem+json`, matching `/data/sources` state

## Remaining boundary

The current dataset consists of imported snapshots of the USGS past-hour summary feed. It
does not claim historical completeness, impact assessment, tsunami forecasting, or marine
safety authority. Scheduled refresh, FDSN historical queries, map rendering, and proximity
analysis remain unfinished.
