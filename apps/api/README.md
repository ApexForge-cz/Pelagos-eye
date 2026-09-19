# OceanScope API

Phase 1 established typed configuration, structured logging, stable error contracts,
health endpoints, migration tooling, and tests. Phase 2 adds the shared source catalog,
source-version, ingestion-run, and quality-issue contracts plus internal official-data
imports and bounded public UN/LOCODE port, USGS earthquake, and Open-Meteo forecast
queries.

Run locally from this directory:

```bash
uv sync
uv run uvicorn oceanscope_api.main:app --reload
```

## Export an ingestion reproducibility manifest

Every ingestion run can be exported as an internal JSON manifest:

```bash
uv run oceanscope-export-manifest --ingestion-run-id <uuid>
```

The manifest includes the source and terms metadata, data/schema version, source URL,
SHA-256 checksum, content-addressed artifact reference, import parameters, code revision,
record counts, run status, and quality issues. The artifact reference is an operator-local
path and must not be exposed through a public API. Exporting a manifest does not change a
source's redistribution status or authorize publication of restricted source records.

## Official port-reference import

After applying migrations to a PostGIS database, import one or both official datasets:

```bash
uv run alembic upgrade head
uv run oceanscope-import-ports --source all --code-revision "$(git rev-parse HEAD)"
```

Required configuration:

- `OCEANSCOPE_DATABASE_URL` points to PostgreSQL/PostGIS.
- `OCEANSCOPE_DATA_DIRECTORY` optionally selects the ignored runtime artifact directory;
  it defaults to `data` relative to the process working directory.
- Standard `HTTPS_PROXY`/`HTTP_PROXY` environment variables may be used where the
  official hosts require the operator's network proxy.

The importer downloads only from the verified official endpoints, bounds artifact size,
stores content-addressed raw files under `raw/<source>/<sha256>.<extension>`, validates
schemas and coordinates, records rejected rows as quality findings, and reuses a
completed run for the same source version, normalizer, and code revision. It does not
merge UN/LOCODE and WPI into canonical port identities.

UN/LOCODE is CC BY 4.0 with attribution. WPI redistribution remains `unreviewed`; keep
its downloaded artifact local until a release-time terms review is completed.

## Read-only status endpoints

- `GET /data/sources` returns the source catalog, official/terms links, attribution,
  redistribution status, computed source state, freshness age and policy thresholds,
  effective cache age, latest ingestion, latest usable version, record counts, and
  quality findings. The current run and latest usable run are separate so a provider
  failure can use a still-valid verified cache without relabeling it as live.
- `GET /system/status` returns the application version, PostGIS and Redis connectivity,
  and one summary per registered provider. Provider summaries use the same computed
  freshness contract as `/data/sources` and include source publication/retrieval times,
  effective cache age, and the latest ingestion run's UTC times and record counts. A
  missing or unreachable dependency is `DEGRADED` / `OFFLINE` with `DATA UNAVAILABLE`.
  Provider state is based on stored ingestion evidence; this endpoint does not contact
  upstream providers on every request.
- `GET /data/sources` returns RFC 9457-style `application/problem+json` with status 503
  when the database cannot answer safely.

These status endpoints expose metadata only. They do not return source records or bypass
the WPI and MarineCadastre redistribution gates.

## Bounded port query

`GET /ports` returns a stable, paginated list of port-reference records. Optional `q`,
`country_code`, and `has_coordinates` filters are available; `limit` is capped at 100 and
`offset` at 100,000. Each result carries source identity, source/version URL, data and
schema versions, publication/retrieval/ingestion/normalization times, source state, cache
age when applicable, attribution, and record quality flags. Raw provider dictionaries and
local artifact references are not exposed.

The repository only returns sources whose recorded redistribution status is `allowed`.
UNECE UN/LOCODE is therefore queryable with its CC BY 4.0 attribution. NGA WPI remains
`unreviewed` and is excluded even when its records exist in the database. This endpoint
does not perform canonical port entity resolution or imply that unrelated source records
refer to the same port.

Public record queries also use the source catalog's computed freshness decision. A usable
cache is labeled `CACHED` with age. If the source has no verified data inside its maximum
stale window, the query returns `503 application/problem+json` rather than stale records.

## Bounded earthquake query

`GET /earthquakes` requires an offset-aware start/end time and a non-antimeridian WGS 84
bounding box. The time window is capped at 31 days; optional minimum magnitude and bounded
pagination filters are available. Results expose event time, provider update time,
ingestion and normalization times separately, plus depth in kilometres, location,
magnitude, provider review status, detail link, quality flags, source state, version, and
attribution. The response states that the USGS `tsunami` field is provider metadata rather
than an OceanScope impact prediction or warning.

## Bounded marine forecast query

`GET /ocean/forecast` requires the original requested coordinate and an offset-aware time
window of at most seven days. It selects the latest successful or partial import matching
that coordinate, so older snapshots are not mixed into the response. Each hourly point
keeps the requested and selected model-grid coordinates distinct and returns explicit
units, valid time, model routing label, provenance, and quality flags. The response warns
about model and coastal limitations and excludes navigation, collision avoidance, and
emergency use.

## Official USGS earthquake import

Import the official all-earthquakes past-hour GeoJSON feed:

```bash
uv run oceanscope-import-earthquakes --code-revision "$(git rev-parse HEAD)"
```

Each feed generation is checksummed and recorded as a source version. Events are keyed by
the stable USGS event ID; only a strictly newer provider `updated` timestamp replaces the
stored observation. Event time, provider update time, feed generation time, retrieval
time, depth in kilometres, WGS 84 point, raw feature, and provenance remain distinct.
Repeated unchanged events are counted without creating duplicates. The `tsunami` field is
stored as provider metadata and is not an OceanScope prediction or warning.
