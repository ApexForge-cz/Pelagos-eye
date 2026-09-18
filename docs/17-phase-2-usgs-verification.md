# Phase 2 USGS earthquake ingestion verification

- Verification date: 2026-09-17
- Official feed: `all_hour.geojson`
- Scope: ingestion, provenance metadata, and bounded read-only event query

## Real-feed evidence

The first observed feed version was
`generated:1789636360000:sha256:76cfdfbe041cbca4` with full SHA-256
`76cfdfbe041cbca4598f3ab597d8a848f6574baf029d47aeeb9ebcedf2974f90`.
It contained three valid events; all three were inserted with no rejection.

One minute later, a newly generated feed contained the same three events. The importer
reported zero inserts, zero updates, three unchanged observations, and zero stale
revisions. The table still contained exactly three events. All locations returned SRID
4326; event time and provider update time were stored independently.

The existing `/data/sources` endpoint automatically reported `usgs-earthquakes` as
`LIVE` / `AVAILABLE` with three accepted records. No event properties were exposed by the
metadata endpoint.

## Automated evidence

- Ruff and strict mypy: passed
- Linux/PostGIS pytest: 42 passed
- Migration downgrade/upgrade and model drift path: passed
- Docker image build: passed
- Real official feed import and one-minute rerun: passed

Tests cover valid parsing, coordinate rejection without zero-fill, generated/checksum
versioning, idempotent same-feed reuse, newer event revision update, a single event row
after revision, and PostGIS SRID 4326.

## Query boundary added

`GET /earthquakes` now exposes stored, normalized events through required time and spatial
bounds, optional minimum magnitude, and bounded pagination. It includes source/version
provenance and an explicit warning that `tsunami` is USGS metadata rather than an impact
prediction. Raw provider features and artifact paths remain internal.

## Remaining boundary

The current slice does not schedule polling, serve cached events, process explicit
deletions/retractions, calculate maritime proximity, or issue tsunami or emergency claims.
Those require separate policy, tests, and user-facing warnings.
