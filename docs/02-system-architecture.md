# System Architecture

## Architecture decision

OceanScope uses a **clean-ish modular monolith** with separate process entry points for the
web API, live ingestion, and heavy batch work where justified. This preserves clear
ownership boundaries for a two-developer team without imposing premature
distributed-system overhead.

## Context

```text
Users
  -> OceanScope web client
      -> OceanScope API / WebSocket gateway
          -> PostgreSQL + PostGIS
          -> Redis
          -> provider adapters
              -> AISStream
              -> MarineCadastre
              -> UN/LOCODE
              -> NGA WPI
              -> Open-Meteo Marine
              -> USGS Earthquake feeds
```

## Runtime containers

| Container/process | Responsibility | Scaling posture |
| --- | --- | --- |
| Web client | interaction, maps, charts, source-state presentation | static assets/CDN later |
| API application | validation, orchestration, queries, health, client WebSocket | one deployable initially |
| Live AIS worker | provider connection, decoding, normalization, persistence/fan-out | one active consumer per subscription shard |
| Batch worker | archive imports, aggregations, anomaly recomputation | scheduled/on demand |
| PostgreSQL/PostGIS | canonical normalized state, tracks, ports, events, spatial queries | primary system of record |
| Redis | bounded cache, ephemeral fan-out/coordination, rate counters | not the only durable record |
| Local data volume; object storage later if justified | checksummed raw artifacts and reproducibility manifests | local volume implemented; object storage remains a measured future decision |

## Backend layers

```text
API routes / WebSocket handlers
  -> application services / use cases
      -> domain policies and analytical rules
          -> repositories
              -> PostgreSQL/PostGIS
      -> provider ports
          -> external provider adapters
```

- **API layer:** transport parsing, authentication context, response models, error mapping. No provider or SQL logic.
- **Service layer:** use-case orchestration, transaction boundaries, freshness policy, authorization decisions.
- **Domain layer:** data-quality rules, status semantics, geofence/anomaly logic, units and invariants.
- **Repository layer:** query construction, persistence, spatial indexing, batch writes.
- **Provider layer:** remote protocols, retries, schema translation, provider health, attribution metadata.

Planned provider contracts include `AISProvider`, `HistoricalAISProvider`, `PortProvider`, `MarineWeatherProvider`, and `EarthquakeProvider`. Provider return types carry data plus provenance; raw provider dictionaries must not leak into API/domain code.

## Frontend structure

```text
app shell and routing
  -> feature modules (live, vessels, ports, ocean, history, analytics, risk, data, system)
      -> feature components and hooks
          -> typed API client / query cache
          -> local UI store
  -> geospatial platform
      -> camera, layer registry, picking, time controller, styling, performance budgets
  -> shared design system
```

- TanStack Query owns server state; Zustand owns focused client/UI state, not duplicated API caches.
- CesiumJS serves the global 3D experience; MapLibre serves 2D analytical views; deck.gl supplies high-volume GPU layers. Libraries are composed behind adapters to avoid feature code depending on every renderer.
- ECharts handles analytical charts; chart configuration remains next to feature semantics, with shared tokens and accessible summaries.

## Proposed bounded modules

| Module | Owns | Does not own |
| --- | --- | --- |
| `vessels` | normalized identity, latest observations, search | provider connection lifecycle |
| `live_ais` | subscriptions, decoding, quality gates, stream health | client presentation |
| `ports` | source records, entity resolution, port queries | vessel visits until explicitly modeled |
| `ocean` | model requests, cache keys, units, attribution | navigation advice |
| `history` | archive manifests, import jobs, track queries | global coverage claims |
| `analytics` | documented aggregations and materialized results | raw-source mutation |
| `risk` | earthquakes, geofences, anomaly evidence | claims of intent or emergency status |
| `provenance` | source catalog, ingestion runs, quality and freshness | hiding provider errors |
| `system` | health/readiness and operational metrics | business analytics |

## Data-flow designs

### Live AIS

1. Worker connects to AISStream with a server-side key and bounded subscription.
2. Binary frame is decoded as UTF-8 JSON; envelope and message type are validated.
3. Raw message metadata is assigned a deterministic event fingerprint where possible.
4. Normalizer emits typed observations with quality flags and provenance.
5. Durable write and latest-state update occur in controlled batches.
6. Redis or in-process broadcaster carries a reduced client-safe event.
7. Client gateway applies authorization/filtering, coalescing, and backpressure.
8. Health records connection state, message lag, dropped/coalesced counts, and last success.

### Historical AIS

1. Register an official download URL, checksum, coverage, and retrieval time in a manifest.
2. Download outside the web request path; keep source archives immutable where terms permit.
3. Scan schema and reject unexpected changes before loading.
4. Normalize timestamps, units, null sentinels, coordinates, and identifiers.
5. Write partitioned staging data, then validated canonical observations.
6. Build spatial/time indexes and derived aggregates with a recorded algorithm version.

### Reference and event data

Release-based sources use versioned snapshots and diff reports. Mutable feeds use upsert semantics based on source identifiers plus provider `updated` timestamps. Deletions or retractions become explicit record states, not silent disappearance.

## Logical data model

This is a plan, not a database migration:

- `data_source`, `source_version`, `ingestion_run`, `quality_issue`
- `vessel`, `vessel_identity_observation`, `vessel_position`
- `port_source_record`, `port`, `port_source_link`
- `marine_forecast_sample`, `earthquake_event`
- `geofence`, `geofence_event`, `anomaly_rule`, `anomaly_event`
- `historical_dataset`, `archive_manifest`, `analytic_run`, `analytic_result`

All time-series/spatial tables include source identity, source/event time, ingestion time, quality flags, and schema/data version. Exact retention and partitioning await volume profiling.

## Spatial and temporal rules

- Canonical geographic storage: WGS 84 / EPSG:4326 with PostGIS `geometry` or `geography` chosen per query semantics.
- Validate latitude `[-90, 90]`, longitude `[-180, 180]`; preserve rejected counts.
- Use `geography` or an appropriate projected CRS for metric distance/area; never measure meters directly in raw degrees.
- Store timestamps as UTC-aware values. Preserve provider strings only in raw records.
- Render antimeridian-crossing tracks as split geometries or wrapped segments.
- Track coordinate/source accuracy separately from numeric precision.

## API design principles

- Version public contracts (`/api/v1`) only when stability is needed; avoid speculative versions internally.
- Use cursor/time-based pagination for dense event streams.
- Require spatial and time bounds on expensive endpoints.
- Return a response metadata envelope containing source status, generated time, effective time, freshness, cache state, and warnings.
- Use stable problem details for errors and correlation IDs for diagnostics.
- Separate liveness from readiness and provider-dependency status.

## Caching

- Cache keys include provider, normalized query, units/model, schema version, and relevant time bucket.
- Stale-while-revalidate is allowed only within source-specific maximum stale age.
- Cache responses preserve the original source timestamp and add `served_from_cache` and cache age.
- Redis failure degrades to uncached behavior where safe; it must not manufacture data.

## Deployment evolution

1. Local Docker Compose for repeatable development.
2. Single-host/container deployment for the first public demo.
3. Managed PostgreSQL/PostGIS and object storage when durability warrants cost.
4. Split a worker or read path only after profiling identifies a bottleneck or availability boundary.

## Architecture risks and trade-offs

- One database simplifies operations but needs partitioning and retention discipline for AIS scale.
- Multiple map engines increase capability and bundle complexity; route-based loading and renderer adapters are required.
- Redis fan-out is simple but not a durable event log; durable persistence precedes acknowledgement for required data.
- A global live subscription may exceed practical bandwidth/storage; initial geographic/message filters must be explicit.
- Provider abstraction must not erase source-specific semantics; canonical fields retain source extensions and raw references.

## Architecture decision status

Accepted ADRs currently cover repository boundaries, toolchain, runtime contracts, local
infrastructure, licensing, provenance, official port ingestion, USGS revision handling,
Open-Meteo snapshots, and bounded MarineCadastre history. Decisions for Cesium/MapLibre/
deck.gl composition, live-event durability, AIS partitioning and retention, authentication,
and production deployment remain phase-scoped work and must be recorded before those
capabilities are released.
