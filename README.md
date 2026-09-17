# OceanScope

> Global Maritime Situational Awareness & Analytics Platform<br>
> 全球港航态势感知与智能分析平台

**Status: 🚧 Phase 2 — Real Data Foundation**

OceanScope is a planned, map-first web platform for exploring live and historical maritime activity, ports, ocean conditions, and risk signals. Phases 0 and 1 are complete. Phase 2 now includes the shared provenance foundation, internal reproducible imports of official UNECE UN/LOCODE and NGA World Port Index records, minute-updated USGS earthquake ingestion, and read-only source/system status APIs. No public event/port-record API, map layer, or production deployment is claimed yet.

## Project Vision

Build a credible open-source maritime intelligence portfolio project that combines a global digital earth with traceable real data. Visual impact must amplify information rather than conceal uncertainty, stale feeds, missing coverage, or unavailable services.

## Why OceanScope

Maritime information is fragmented across streaming AIS, large historical archives, port reference datasets, model-based ocean forecasts, and hazard feeds. OceanScope plans to normalize those sources behind a consistent provenance model and expose them through focused operational and analytical workflows.

The project is intentionally designed for one developer: a modular monolith, replaceable external-data providers, background workers where justified, and one primary spatial database instead of a premature microservice estate.

## Planned Features


| Capability                                            | Status               |
| ----------------------------------------------------- | -------------------- |
| Global 3D digital earth and 2D analytical map         | Planned              |
| Live AIS ingestion, filtering, and WebSocket delivery | Planned              |
| Vessel and port search/detail views                   | Planned              |
| Historical AIS playback and traffic analytics         | Planned              |
| Heatmaps, routes, trends, and geofences               | Planned              |
| Waves, swell, sea-surface temperature, and currents   | Planned              |
| Global earthquake reference ingestion                 | Implemented, internal |
| Speed, course, dwell, and AIS-gap anomaly detection   | Planned              |
| Data provenance, freshness, and system health         | In progress          |
| Official port-reference ingestion                     | Implemented, internal |
| Source catalog and system status APIs                  | Implemented, internal |
| Assisted maritime situation analysis                  | Planned, later phase |

## Architecture Preview

```text
Web client
  React + TypeScript
  pages/features -> components -> hooks -> API client/store
  CesiumJS | MapLibre GL JS | deck.gl | ECharts
            |
       HTTP + WebSocket
            |
Modular FastAPI application
  API -> services -> repositories -> PostgreSQL/PostGIS
                  -> Redis cache/stream coordination
                  -> external provider adapters
            |
  ingestion and analytical workers
```

The planned deployment unit is a modular monolith plus independently runnable workers. Provider interfaces isolate AIS, marine weather, port, and hazard integrations so data sources can be replaced without rewriting product logic.

## Technology Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide, Framer Motion
- State and data: Zustand, TanStack Query
- Visualization: CesiumJS, MapLibre GL JS, deck.gl, Apache ECharts
- Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic, httpx, websockets
- Storage: PostgreSQL/PostGIS and Redis; Parquet/DuckDB for offline analytical staging when appropriate
- Data: Polars first for high-volume transforms; Pandas/GeoPandas/Shapely where their ecosystems are useful
- Quality: pytest, Vitest, React Testing Library, Playwright, Ruff, ESLint, Prettier, strict TypeScript, practical mypy
- Delivery: Docker, Docker Compose, GitHub Actions

Foundation choices are recorded in accepted Architecture Decision Records. Later-phase GIS, provider, analytical, and deployment choices remain planned until their evidence and phase gates exist.

## Real Data Sources


| Source                     | Planned use                                     | Coverage / caveat                                                             |
| -------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| AISStream                  | Live AIS over server-side WebSocket             | Global feed; API key required; no SLA or durable replay                       |
| MarineCadastre / AccessAIS | Historical tracks and traffic analysis          | United States waters, not a global archive; bulk service is primary fallback  |
| UNECE UN/LOCODE            | Trade and transport location identifiers        | Global; release-based; not every entry is a seaport                           |
| NGA World Port Index       | Port coordinates, facilities, and services      | Global; official CSV updated monthly; planning aid, not navigation authority  |
| Open-Meteo Marine API      | Waves, swell, sea-surface temperature, currents | Model data; coastal limitations; free tier is non-commercial and rate-limited |
| USGS Earthquake GeoJSON    | Global earthquake context                       | Summary feed updates every minute; event records can be revised               |

See [docs/03-data-sources.md](docs/03-data-sources.md) for verified endpoints, fields, limitations, licenses, and fallback policies.

## Roadmap


| Phase | Focus                  | Status   |
| ----- | ---------------------- | -------- |
| 0     | Research & Planning    | Complete |
| 1     | Engineering Foundation | Complete |
| 2     | Real Data Foundation   | In progress |
| 3     | Digital Earth          | Planned  |
| 4     | Live AIS               | Planned  |
| 5     | Historical Analytics   | Planned  |
| 6     | Risk & Anomaly Engine  | Planned  |
| 7     | Advanced Visualization | Planned  |
| 8     | Intelligence           | Planned  |
| 9     | QA & Security          | Planned  |
| 10    | Production Release     | Planned  |

Detailed objectives, dependencies, risks, acceptance criteria, and definitions of done are in [docs/06-development-roadmap.md](docs/06-development-roadmap.md).

## Development Status

Phases 0 and 1 are complete. Phase 2 has connected three official sources behind the source catalog, source-version, ingestion-run, and quality-issue contracts. UN/LOCODE, WPI, and the USGS past-hour earthquake feed can be imported into PostGIS with checksummed raw artifacts, strict validation, and idempotent/revision-aware writes. Read-only `/data/sources` and `/system/status` APIs expose provenance and honest availability without exposing WPI or event records. Public record APIs, entity resolution, map features, production deployment, and live AIS remain unfinished.

## Development Quick Start

Prerequisites: Python 3.13, [uv](https://docs.astral.sh/uv/), Node.js 24 with npm, and optionally Docker Compose.

```bash
uv sync --directory apps/api --python 3.13
npm ci
python scripts/check.py
```

Run the minimal development processes in separate terminals:

```bash
uv run --directory apps/api uvicorn oceanscope_api.main:app --reload
npm run web:dev
```

The API exposes only `/health/live` and `/health/ready`. The web application is an engineering-status shell and intentionally contains no simulated business dashboard.

## Data Integrity Principles

- Never fabricate production vessel positions, KPIs, alerts, weather, or port data.
- Use official sources where possible and verify their documentation before integration.
- Preserve source, source URL, source timestamp, ingestion timestamp, update timestamp, cache state, and data version.
- Every external-data surface must show `LIVE`, `CACHED`, `DELAYED`, or `OFFLINE`.
- On provider failure, show the last verified cache with its age, or `DATA UNAVAILABLE`.
- Test fixtures are allowed only under test paths and must be clearly labeled `TEST DATA`.

## Planned Screens

`/` Overview · `/live` Live Maritime Traffic · `/vessels` Vessel Explorer · `/vessels/:mmsi` Vessel Detail · `/ports` Port Intelligence · `/ports/:id` Port Detail · `/ocean` Ocean Environment · `/history` Historical AIS Playback · `/analytics` Traffic Analytics · `/risk` Risk Center · `/data` Data Sources & Provenance · `/system` System Health

## Documentation

The `docs/` directory contains the project charter, product requirements, architecture, source verification, governance, design system, roadmap, testing and security plans, GitHub strategy, risk register, Codex skill specifications, project-wide completion criteria, ADRs, phase verification records, and the direct dependency inventory.

## License

Original source code is licensed under the [MIT License](LICENSE), as selected in the remote repository. This permits commercial reuse by others even though the owner's project development and deployment are non-commercial. Third-party data remains governed by each provider's terms. See [ADR-0005](docs/adr/0005-license.md).

## Disclaimer

OceanScope is a planned educational and analytical project. It is not a navigation, collision-avoidance, emergency-response, regulatory, or operational decision system. AIS can be incomplete or incorrect; forecast and hazard data carry uncertainty; port reference data does not replace current charts, notices, or competent authorities.
