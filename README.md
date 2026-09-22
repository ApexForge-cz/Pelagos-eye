# OceanScope

> Global Maritime Situational Awareness & Analytics Platform<br>
> 全球港航态势感知与智能分析平台

**Status: Phase 3 Complete — Digital Earth**

OceanScope is a map-first web platform for exploring maritime activity, ports, ocean conditions, and risk signals. Phases 0 through 3 are complete. Phase 2 delivered the shared provenance foundation, reproducible imports from five official source families, bounded public queries, and a minimal real-data status UI. Phase 3 delivered accepted 2D and focused 3D spatial workspaces over real port, earthquake, and marine-forecast data. No public WPI or restricted historical-AIS record API, live AIS layer, or production deployment is claimed yet.

## Project Vision

Build a credible open-source maritime intelligence portfolio project that combines a global digital earth with traceable real data. Visual impact must amplify information rather than conceal uncertainty, stale feeds, missing coverage, or unavailable services.

## Why OceanScope

Maritime information is fragmented across streaming AIS, large historical archives, port reference datasets, model-based ocean forecasts, and hazard feeds. OceanScope plans to normalize those sources behind a consistent provenance model and expose them through focused operational and analytical workflows.

The project started with Developer A as its sole author and is now developed by two people.
It remains a modular monolith with replaceable external-data providers, independently
runnable workers only where justified, and one primary spatial database instead of a
premature microservice estate.

## Planned Features


| Capability                                            | Status               |
| ----------------------------------------------------- | -------------------- |
| 2D analytical map and bounded spatial workspace       | Implemented, local   |
| Focused 3D digital earth                              | Implemented, local   |
| Live AIS ingestion, filtering, and WebSocket delivery | Planned              |
| Vessel and port search/detail views                   | Planned              |
| Bounded U.S.-water historical AIS ingestion           | Implemented, internal |
| Historical AIS playback and traffic analytics         | Planned              |
| Heatmaps, routes, trends, and geofences               | Planned              |
| Bounded marine forecast ingestion                     | Implemented, internal |
| Bounded marine forecast query API                     | Implemented, local    |
| Ocean map layers                                      | Planned              |
| Global earthquake reference ingestion                 | Implemented, internal |
| Bounded USGS earthquake query API                     | Implemented, local    |
| Speed, course, dwell, and AIS-gap anomaly detection   | Planned              |
| Data provenance, freshness, and system health         | Implemented, local   |
| Official port-reference ingestion                     | Implemented, internal |
| Bounded UN/LOCODE port query API                      | Implemented, local    |
| Source catalog and system status APIs                  | Implemented, internal |
| Real-data source status web UI                         | Implemented, local    |
| Coordinate and viewport query UI                       | Implemented, local   |
| Region Workspace and shared spatiotemporal context     | Planned, Phase 3      |
| Source Lens and Data Confidence Layer                  | Planned, Phase 3+     |
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

The installed Phase 3 frontend runtime is React, TypeScript, Vite, Three.js, and MapLibre.
CesiumJS, deck.gl, ECharts, Tailwind, shadcn/ui, Framer Motion, Zustand, and TanStack Query
remain target choices for later requirements and are not installed merely because they
appear below.

- Frontend: React, TypeScript, Vite, Tailwind CSS, shadcn/ui, Lucide, Framer Motion
- State and data: Zustand, TanStack Query
- Visualization: Three.js and MapLibre GL JS installed; CesiumJS, deck.gl, and Apache ECharts conditional
- Backend: Python 3.12+, FastAPI, Pydantic, SQLAlchemy, Alembic, httpx, websockets
- Storage: PostgreSQL/PostGIS and Redis; Parquet/DuckDB for offline analytical staging when appropriate
- Data: Polars first for high-volume transforms; Pandas/GeoPandas/Shapely where their ecosystems are useful
- Quality: pytest, Vitest, React Testing Library, Playwright, Ruff, ESLint, Prettier, strict TypeScript, practical mypy
- Delivery: Docker, Docker Compose, GitHub Actions

Foundation choices are recorded in accepted Architecture Decision Records. Later-phase GIS, provider, analytical, and deployment choices remain planned until their evidence and phase gates exist.

## 3D Vision

Phase 3 delivers an **Oceanic Spatial Intelligence Command Center**: a map-first desktop
workspace with a focused Three.js globe or MapLibre analytical map occupying roughly 55%-65%
of the viewport, a context-sensitive left rail, a selection-driven intelligence rail, a
top command bar, and a restrained bottom module dock. It will borrow the useful spatial
ideas of cinematic globe-to-region transitions, layered HUD information, region highlight,
and route context without copying aviation terminology, assets, or decorative telemetry.

Visual depth, camera, lighting, motion, and real data density should create impact. Constant
flashing, excessive neon, ornamental scan lines, invented KPIs, and effects that obscure
source, coverage, time, or uncertainty are prohibited.

## Innovation Roadmap

Innovation follows data reliability rather than feature count: Region Workspace,
Spatiotemporal Lens, Data Confidence Layer, Corridor Intelligence, Source Lens, Compare
Mode, Environmental Context, Explainable Anomaly, Evidence-based Intelligence, and only
then Natural Language Spatial Query research. No derived percentage, activity score, or AI
summary may invent its numerical evidence.

## Two-Developer Collaboration

Developer A remains Project Lead and Full-Stack GIS Engineer with approximately 65%-70% of
the planned workload: product and system architecture, core React/TypeScript, UI/UX, GIS,
3D, spatial interaction, core API contracts and analytics, integration, demo, and release.
Developer B is Data & Platform Engineer with approximately 30%-35%: new providers,
ingestion, validation, normalization, provenance, data quality, PostGIS/Redis operations,
workers, infrastructure, backend data services, provider/backend tests, and performance
pipelines.

Existing Ownership Wins: stable modules remain with their current owner. New work follows
the ownership map; shared contracts, migrations, root configuration, README, AGENTS, and
GitHub files use focused pull requests and review. The team uses short-lived functional
branches, contract-first integration, one migration author at a time, and no direct push to
`main`.

## Real Data Sources


| Source                     | Planned use                                     | Coverage / caveat                                                             |
| -------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------- |
| Pelyr OPEN-AIS             | Bounded live AIS over server-side WebSocket      | Self-service key; mixed licences; no SLA, global guarantee, or durable replay |
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
| 2     | Real Data Foundation   | Complete |
| 3     | Digital Earth          | Complete |
| 4     | Live AIS               | Planned  |
| 5     | Historical Analytics   | Planned  |
| 6     | Risk & Anomaly Engine  | Planned  |
| 7     | Advanced Visualization | Planned  |
| 8     | Intelligence           | Planned  |
| 9     | QA & Security          | Planned  |
| 10    | Production Release     | Planned  |

Detailed objectives, dependencies, risks, acceptance criteria, and definitions of done are in [docs/06-development-roadmap.md](docs/06-development-roadmap.md).

## Development Status

Phases 0 through 3 are complete. Phase 3 Digital Earth passed its final gate on 2026-09-19 with typed viewport contracts, real port/earthquake/marine data, 3D/2D fallback, selection details, legends, attribution, freshness, explicit offline/coverage states, reduced-motion handling, interaction recovery, and an accessible non-map representation. Phase 4 remains planned; a provider-neutral client contract and shared cross-language `TEST DATA` fixtures are recorded in `docs/31-phase-4-contract-kickoff.md` and `docs/32-phase-4-contract-verification.md`. Pelyr OPEN-AIS is the selected provider candidate, and the revised first slice uses a fixed Gulf of Finland box with zero persistent live-AIS storage. Its terms/source review and accepted 2026-09-22 credential-backed smoke evidence are recorded in `docs/36-pelyr-live-ais-provider-verification.md`; the smoke confirmed the `/v1` protocol, runtime limits/source directory, `collector_receiver` key scope, heartbeat, accepted fixed subscription, and non-empty observations. The provider adapter may now proceed only through an explicitly authorized implementation issue and focused pull request. No live AIS provider, route, WebSocket, storage, or UI is implemented or claimed. Cesium, deck.gl, scheduled refresh, entity resolution, and production deployment also remain unfinished. The Phase 2 foundation remains the source of truth for provenance, redistribution gates, cache semantics, and `DATA UNAVAILABLE` behavior. `/system/status` reports PostGIS and Redis connectivity plus provider freshness and latest-ingestion summaries. See `docs/28-phase-3-spatial-slice-verification.md`, `docs/29-phase-3-globe-verification.md`, and `docs/30-phase-3-gate-verification.md` for accepted Phase 3 evidence and limitations.

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

The API exposes `/health/live`, `/health/ready`, `/ports`, `/earthquakes`, `/ocean/forecast`, `/data/sources`, and `/system/status`.
The web application is the first Phase 3 map-first spatial workspace backed by the public
Phase 2 APIs. It renders only bounded stored records, exposes source and coverage state,
and does not create simulated maritime records or operational claims.

Export an internal reproducibility manifest for a known ingestion run with:

```bash
uv run --directory apps/api oceanscope-export-manifest --ingestion-run-id <uuid>
```

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

The audited V2.1 master plan is
[`docs/OceanScope_Project_Plan_v2.1.md`](docs/OceanScope_Project_Plan_v2.1.md). Its rendered
PDF is generated at `output/pdf/OceanScope_Project_Plan_v2.1.pdf`; the root Chinese-named
PDF is synchronized for compatibility with the original repository artifact.

## License

Original source code is licensed under the [MIT License](LICENSE), as selected in the remote repository. This permits commercial reuse by others even though the owner's project development and deployment are non-commercial. Third-party data remains governed by each provider's terms. See [ADR-0005](docs/adr/0005-license.md).

## Disclaimer

OceanScope is a planned educational and analytical project. It is not a navigation, collision-avoidance, emergency-response, regulatory, or operational decision system. AIS can be incomplete or incorrect; forecast and hazard data carry uncertainty; port reference data does not replace current charts, notices, or competent authorities.
