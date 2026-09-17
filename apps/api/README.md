# OceanScope API

Phase 1 established typed configuration, structured logging, stable error contracts,
health endpoints, migration tooling, and tests. Phase 2 is adding the shared source
catalog, source-version, ingestion-run, and quality-issue contracts before any maritime
provider adapter or business route is exposed.

Run locally from this directory:

```bash
uv sync
uv run uvicorn oceanscope_api.main:app --reload
```
