# Phase 2 source freshness and cache-fallback verification

- Verification date: 2026-09-18
- Scope: `GET /data/sources` and the local source-status UI
- Controlled states: `LIVE`, `DELAYED`, `CACHED`, `OFFLINE`

## Implemented policy

The status service computes effective state at request time. It uses the latest usable
version retrieval time, initial cache age when present, elapsed time, the latest ingestion
attempt, and the source policy below. A failed or running refresh falls back to the last
verified version only inside the maximum stale window and labels it `CACHED` with age.
Data outside the window is `OFFLINE` and `DATA UNAVAILABLE`.

| Source | `LIVE` through | `DELAYED` through | Maximum verified cache |
| --- | ---: | ---: | ---: |
| USGS past-hour earthquake feed | 5 minutes | 15 minutes | 1 hour |
| Open-Meteo marine forecast | 6 hours | 24 hours | 48 hours |
| UNECE UN/LOCODE release | 200 days | 240 days | 400 days |
| NGA World Port Index release | 35 days | 65 days | 180 days |
| NOAA MarineCadastre dated archive | 1 day | 1 day | No time expiry |

MarineCadastre's exception applies only to a checksum-pinned archive for its declared
historical date. It is shown as stored `CACHED` data after one day and does not imply live
upstream availability, complete receiver coverage, or public redistribution permission.
Unknown sources receive a conservative default of 1 day live, 7 days delayed, and 30 days
maximum cache age.

The API returns the current data age, all policy thresholds, and effective cache age. The
UI uses those server-computed values rather than maintaining a second policy clock.

## Verification evidence

- source-state tests cover absent data, failed-refresh fallback, `DELAYED` to `CACHED` to
  `OFFLINE` transitions, cache age, and the immutable historical-archive exception
- backend Ruff format and lint checks: passed
- backend strict mypy: passed for 84 source files
- Linux backend suite: 79 passed, 1 skipped
- skipped test: destructive migration integration requires an explicitly named disposable
  PostGIS test database; its earlier Phase 2 run passed and this change adds no migration
- frontend Prettier and ESLint checks: passed
- frontend Vitest: 2 passed
- frontend strict TypeScript and Vite production build: passed

## Remaining boundary

This policy evaluates stored evidence; it does not schedule refreshes or actively probe a
provider between runs. The public port, earthquake, and marine-forecast query services use
the same computed state: acceptable cached results are age-labeled, and data outside the
maximum window returns `503 application/problem+json` instead of stale records.
