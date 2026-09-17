# OceanScope API

Phase 1 established typed configuration, structured logging, stable error contracts,
health endpoints, migration tooling, and tests. Phase 2 adds the shared source catalog,
source-version, ingestion-run, and quality-issue contracts plus internal official-data
imports. No public port route is exposed yet.

Run locally from this directory:

```bash
uv sync
uv run uvicorn oceanscope_api.main:app --reload
```

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
merge UN/LOCODE and WPI into canonical port identities and does not publish either
dataset through an API.

UN/LOCODE is CC BY 4.0 with attribution. WPI redistribution remains `unreviewed`; keep
its downloaded artifact local until a release-time terms review is completed.

## Read-only status endpoints

- `GET /data/sources` returns the source catalog, official/terms links, attribution,
  redistribution status, controlled source state, latest ingestion, latest usable
  version, record counts, and quality findings. The current run and latest usable run
  are separate so a provider failure never relabels old data as live.
- `GET /system/status` returns the application version and database availability. A
  missing or unreachable database is `DEGRADED` / `OFFLINE` with `DATA UNAVAILABLE`.
- `GET /data/sources` returns RFC 9457-style `application/problem+json` with status 503
  when the database cannot answer safely.

These endpoints expose metadata only. They do not return port records or bypass the WPI
redistribution gate.
