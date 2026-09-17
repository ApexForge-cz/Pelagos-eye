# Phase 2 Open-Meteo marine forecast verification

- Verification date: 2026-09-17
- Official endpoint: `https://marine-api.open-meteo.com/v1/marine`
- Scope: internal bounded point-forecast ingestion and provenance; no public forecast API

## Real-response evidence

A real 24-hour request at WGS 84 coordinate `20.000000, -40.000000` used GMT/UTC,
`cell_selection=sea`, and the `best_match` routing mode. Open-Meteo selected grid
coordinate `20.041664, -40.041656`.

The latest reviewed source version was
`forecast:2026-09-17T13:00:2026-09-18T12:00:sha256:9a2a6dae7fcbfcee` with full raw
artifact SHA-256
`9a2a6dae7fcbfcee344e728bacf2c9ad960622676e8e46e054d09a7d9ae001a9`.
All 24 hourly rows were accepted and inserted; none were rejected. The database reported
SRID 4326, UTC valid times from `2026-09-17 13:00` through `2026-09-18 12:00`, and wave
heights from 1.46 m to 1.74 m for that response. These are time-bound model values, not
permanent facts or observations.

The source catalog recorded `open-meteo-marine` as `LIVE` / succeeded with 24 received
and 24 accepted rows. The raw JSON artifact, source URL including the request, request
key, variables, units, retrieval time, and normalization version remain traceable.

## Automated evidence

- Ruff and strict mypy: passed
- Unit and service-independent tests: 50 passed, one integration test skipped when no
  disposable database was supplied
- Disposable PostGIS migration/integration suite: 51 passed
- Production API Docker image build: passed
- Real official API request and database import: passed

Tests cover request bounds, UTC and sea-cell parameters, unit/grid preservation,
out-of-range rejection without clamping, all-null row rejection without zero-fill,
changed-unit and truncated-response rejection, duplicate-time isolation, explicit
variable subsets, same-content idempotency, PostGIS SRID 4326, and migration
downgrade/upgrade.

## Remaining boundary

This slice does not schedule refreshes, expose forecasts publicly, choose a cache by age,
fall back across models, or provide dense map tiles. Coastal/model uncertainty remains;
the data must not be used for navigation, collision avoidance, or emergency decisions.
The free endpoint is for non-commercial use and requires attribution under the current
terms reviewed on the verification date.
