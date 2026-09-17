# Phase 2 official port-source verification

- Verification date: 2026-09-17
- Scope: internal UN/LOCODE and World Port Index download, validation, provenance, and
  PostGIS persistence
- Environment: Docker Linux API image, PostgreSQL 17 with PostGIS 3.5
- Public API/UI: not included

## Official artifacts observed

| Source | Version | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| UNECE UN/LOCODE | `2025-1` | 13,507,338 | `ad409fc7149b10f98d61190c34d9daf78b78bb8b31464cc66de1a89d09b01b5d` |
| NGA World Port Index | content-addressed snapshot | 1,306,123 | `23bba5f0ce278590c5bccc69c0deb7142087af9a4101600e1264fa062fec52ee` |

Artifacts were downloaded from the official endpoints documented in
`docs/03-data-sources.md`, written under ignored `data/raw` paths, and revalidated by
checksum. They are not repository fixtures and must not be committed.

## Import evidence

| Source | Received | Accepted | Rejected | Skipped | Stored with geometry | Result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| UN/LOCODE | 116,284 | 17,600 | 52 | 98,632 non-port rows | 11,798 | `partial`, `LIVE` |
| WPI | 2,951 | 2,926 | 25 | 0 | 2,926 | `partial`, `LIVE` |

`partial` is intentional: strict validation surfaced source-quality findings instead of
filling or inventing values. UN/LOCODE reported 35 invalid optional coordinates and 52
unknown/invalid function encodings; WPI reported 25 invalid coordinates and four
UN/LOCODE identity conflicts. The stored unique source keys exactly matched accepted-row
counts.

All non-null locations returned SRID 4326. A second complete import returned the same
ingestion-run IDs and row counts for both sources, demonstrating idempotent reuse with no
duplicate source records.

Two WPI attempts made before the operator's existing HTTPS proxy was passed into the
container failed DNS resolution. Both failures were retained as `failed` / `OFFLINE`
ingestion runs with zero accepted records. The later proxied attempt succeeded and was
recorded separately as `LIVE`; the importer did not fall back to cached or fabricated
values.

## Automated checks

- Ruff: passed
- mypy: passed for 31 source files
- Linux/PostGIS pytest suite: 32 passed
- Docker image build: passed
- Alembic upgrade/downgrade/upgrade and drift check: passed
- Real imports and idempotent rerun: passed

The automated suite uses only fixtures labeled `TEST DATA`; production imports use the
official network providers. The real artifacts and local database are disposable runtime
evidence, not test fixtures.

## Remaining Phase 2 work

- Add the planned frontend `/data` and `/system` screens; the read-only backend
  `/data/sources` and `/system/status` contracts are now implemented.
- Integrate a bounded MarineCadastre import, Open-Meteo Marine, and USGS earthquakes.
- Define cache/TTL policy and visible `CACHED`, `DELAYED`, and `OFFLINE` behavior per
  source.
- Complete WPI redistribution review before any public data response or snapshot release.
- Defer canonical port entity resolution until an explicit matching/evaluation design is
  approved.
