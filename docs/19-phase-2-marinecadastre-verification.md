# Phase 2 NOAA MarineCadastre historical AIS verification

- Verification date: 2026-09-17
- Official metadata: `https://www.fisheries.noaa.gov/inport/item/73064`
- Official bulk index: `https://noaaocm.blob.core.windows.net/ais/csv2/csv2024/index.html`
- Scope: internal bounded historical-point ingestion; no public playback API

## Real-archive evidence

The verified archive was the official 2024-01-14 daily Zstandard CSV, 151,376,897 bytes,
with SHA-256
`2fd0fafeeefd2c79d3318b6eda318977d568e8ec3687c966378cb99a0b60dc4b`.
Its current snake-case header was matched through explicit aliases rather than accepted as
an arbitrary schema.

The import requested WGS 84 bounds longitude -91 to -89 and latitude 28 to 30, UTC time
2024-01-14 00:00 inclusive through 01:00 exclusive, with a 5,000-record cap. It streamed
and inspected 5,742,930 source rows. Of 28,326 matching rows, two exact duplicates were
identified, 5,000 records were stored, and 23,324 were explicitly reported as capped.
There were no invalid required fields in the requested slice. The stored sample contains
804 distinct MMSIs, covers source times 00:00:00 through 00:12:59 UTC, remains inside the
requested box, and uses SRID 4326. Its shorter effective time coverage is a direct result
of the cap and is therefore disclosed through a 23,324-row `coverage_unknown` issue. The
result is a reproducible sample, not complete traffic coverage.

The first successful parse reused the checksummed local artifact after the current NOAA
header was verified. That replay is recorded as `CACHED` with cache age; it is not
misrepresented as a fresh network response.

## Automated evidence

- Ruff and strict mypy: passed
- Linux/PostGIS suite: 58 passed with 80% total coverage
- Alembic downgrade/upgrade and model-drift checks: passed
- Production-style API Docker image build: passed
- Real official archive download, checksum, streaming parse, and database import: passed

Tests cover geographic/time/record bounds, verified URL construction, compressed-size
limits, old and current column aliases, provider-revision failure, filtering, invalid-row
rejection, AIS sentinels, exact duplicates, cap truncation, local checksummed archive reuse,
idempotent writes, and PostGIS SRID 4326.

## Remaining boundary

The slice does not provide public record queries, track construction, playback, analytics,
near-duplicate detection, or a retention scheduler. MarineCadastre coverage is historical
and U.S.-focused; receiver gaps mean missing records are not evidence that a vessel was
absent. Raw archives and records remain internal under the reviewed redistribution limits.
