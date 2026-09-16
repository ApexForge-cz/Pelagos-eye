# Product Requirements

## Product goal

OceanScope will provide a unified, map-first workspace for live vessel awareness, historical traffic exploration, port intelligence, marine conditions, and contextual risk events. The experience must remain useful when a provider is delayed or unavailable by showing honest state rather than synthetic substitutes.

## Personas and jobs

| Persona | Primary job | Evidence needed |
| --- | --- | --- |
| Explorer | Find a vessel or port and understand current context | identity, position, time, source, coverage |
| Analyst | Compare traffic across an area and period | stable filters, aggregations, denominators, export metadata |
| Researcher | Reproduce a track or derived indicator | versioned inputs, parameters, code/version, timestamps |
| Maintainer | Diagnose broken or stale feeds | ingestion lag, failures, cache age, provider status |

## Functional requirements

### FR-1 Global geospatial workspace

- Provide a 3D globe for global situational context and a 2D map for precise analytical workflows.
- Support layer visibility, legend, time context, source attribution, camera bookmarks, and URL-shareable filters.
- Keep coordinate handling in WGS 84 at provider boundaries, documenting any derived projection.
- Cluster, aggregate, tile, or GPU-render large layers rather than creating one UI component per feature.

### FR-2 Live maritime traffic

- Ingest AIS through a backend-only WebSocket connection.
- Normalize supported position and static messages while preserving raw-message references.
- Deliver authorized, filtered updates to clients through the application's WebSocket gateway.
- Show last position time, received time, source, freshness, and coverage caveats.
- Reconnect with bounded exponential backoff and jitter; never imply continuity across gaps.

### FR-3 Vessel exploration

- Search by MMSI, IMO identifier when available, call sign, and vessel name.
- Present identity, dimensions, type, navigation status, latest verified position, speed, course, heading, and recent track where present.
- Treat mutable or missing identity fields as observations, not permanent truth.
- Mark fields unavailable instead of inferring them from unrelated values.

### FR-4 Port intelligence

- Search and filter ports/locations using WPI and UN/LOCODE.
- Distinguish a UN/LOCODE location from a confirmed maritime port using function codes and source joins.
- Present coordinates, facilities/services, source edition, and source-specific caveats.
- Retain both source identifiers; do not collapse records through name-only matching.

### FR-5 Historical AIS playback

- Begin with verified MarineCadastre data for U.S. waters.
- Filter by time, area, vessel, and supported attributes.
- Provide play, pause, seek, speed control, temporal window, and track inspection.
- Display archive coverage and any sampling/downsampling applied.

### FR-6 Traffic analytics

- Derive counts, density, speed distributions, traffic corridors, dwell summaries, and time trends from the selected dataset.
- State the unit of analysis: message, unique MMSI, trip/segment, cell, or time bucket.
- Make spatial boundary, time zone, deduplication, and missing-value rules inspectable.
- Avoid comparing results produced with different inputs or denominators without explicit labels.

### FR-7 Ocean environment

- Request wave, swell, sea-surface temperature, ocean-current velocity/direction, and relevant sea-level fields from verified Open-Meteo Marine endpoints.
- Expose model, run/update time where available, resolution, units, and coastal-use warning.
- Cache by coordinate/grid, variable set, model, and time window.

### FR-8 Risk events

- Display USGS earthquake events with magnitude, depth, place, event time, update time, review status, and tsunami flag when present.
- Keep hazard context separate from assertions of impact on a vessel or port.
- Link to authoritative event detail.

### FR-9 Geofences and anomalies

- Support polygon/circle geofences and entry, exit, dwell, and rule evaluations.
- Planned detectors: speed-rule violation, abrupt course change, prolonged dwell, and observation gap.
- Each alert must include rule version, threshold, evidence window, supporting observations, confidence/quality flags, and status.
- Alerts are analytical indicators, not proof of wrongdoing or emergencies.

### FR-10 Provenance and health

- Provide `/data` for source catalog, coverage, attribution, license note, latest successful ingestion, latency, and status.
- Provide `/system` for provider connectivity, queue/worker state, data freshness, cache health, database health, and application version.
- Use the controlled status vocabulary `LIVE`, `CACHED`, `DELAYED`, `OFFLINE`.

### FR-11 Intelligence, later phase

- Generate summaries only from retrieved, timestamped OceanScope evidence.
- Cite source records and clearly separate facts, calculations, uncertainty, and suggestions.
- Do not let generated text create operational instructions or unsupported causal claims.

## Planned routes

| Route | Purpose | Phase |
| --- | --- | --- |
| `/` | Overview and source health | 3–4 |
| `/live` | Live traffic workspace | 4 |
| `/vessels` | Vessel search/explorer | 4 |
| `/vessels/:mmsi` | Vessel detail | 4 |
| `/ports` | Port search and global context | 2–3 |
| `/ports/:id` | Port detail | 3 |
| `/ocean` | Marine conditions | 3 |
| `/history` | Historical playback | 5 |
| `/analytics` | Traffic analytics | 5–7 |
| `/risk` | Events, geofences, anomalies | 6 |
| `/data` | Sources and provenance | 2 |
| `/system` | System health | 2–4 |

## Non-functional requirements

### Correctness

- Validate coordinates, timestamps, enumerations, plausible ranges, identifiers, and schema versions at ingestion.
- Use UTC internally and ISO 8601 timestamps with offsets at boundaries.
- Record transformations and quality flags; raw immutable references must remain traceable.

### Performance

- Define browser feature-count, frame-rate, memory, payload, and interaction budgets from reference-hardware profiling.
- Use spatial indexes, bounding/time filters, pagination, server aggregation, vector/binary formats where justified, and level-of-detail rendering.
- Backpressure or shed nonessential live updates before exhausting memory.

### Availability and resilience

- Provider failure must not crash unrelated modules.
- Timeouts, retry limits, circuit behavior, and cache policy are provider-specific.
- Retain last-known verified data only within a documented stale window and label it.

### Security and privacy

- Keep all provider secrets server-side; redact them from logs and errors.
- Use allowlisted origins, bounded queries, rate limits, dependency scanning, and least-privilege credentials.
- Do not add user tracking or personal profiles without a separate privacy review.

### Accessibility and responsiveness

- Target WCAG 2.2 AA for non-map UI; provide keyboard paths, visible focus, readable contrast, reduced motion, and textual alternatives for essential map facts.
- Desktop is the primary dense-analysis surface; smaller screens receive simplified, usable layouts rather than a squeezed command center.

### Maintainability

- Keep domain logic framework-light and testable.
- Keep routes/controllers thin, database access in repositories, and external calls in providers.
- Every new dependency needs a recorded purpose and simpler-alternative check.

## Product states

| State | Meaning | UI behavior |
| --- | --- | --- |
| `LIVE` | Within source-specific freshness threshold | show timestamp and normal styling |
| `CACHED` | Last verified data served after cache hit/provider failure | show cache age and source time |
| `DELAYED` | Data is arriving but exceeds expected freshness | show warning and measured lag |
| `OFFLINE` | No acceptable current or cached data | show `DATA UNAVAILABLE`; retain controls/context |

## Initial acceptance scenarios

1. A provider outage yields labeled cached data or an unavailable state, never generated values.
2. A vessel position can be traced to its provider message and timestamps.
3. A port view preserves both UN/LOCODE and WPI lineage when records are linked.
4. Historical analytics disclose U.S.-water coverage and calculation settings.
5. An anomaly card shows its evidence and rule version and avoids declaring intent.
6. A user can distinguish event time, provider update time, ingestion time, and UI refresh time.

## Open product decisions

- Primary audience for the first public demo: portfolio reviewers, maritime researchers, or general explorers.
- Whether deployment is non-commercial only; this affects Open-Meteo plan choice.
- Geographic demo focus for live traffic and storage budgets.
- Retention period for raw and normalized AIS.
- Whether accounts, saved workspaces, exports, and share links belong in v1.
- Languages for the initial UI and documentation.

