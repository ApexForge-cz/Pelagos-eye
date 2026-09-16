# OceanScope API

Phase 1 contains only the API engineering foundation: typed configuration,
structured logging, stable error contracts, health endpoints, migration tooling,
and tests. Maritime data providers and business routes begin in later phases.

Run locally from this directory:

```bash
uv sync
uv run uvicorn oceanscope_api.main:app --reload
```
