# Risk Register

Scales: likelihood and impact are `Low`, `Medium`, or `High`. Initial owner is the repository maintainer. Review at every phase gate and after source, architecture, or deployment changes.

| ID | Risk | Likelihood | Impact | Early indicator | Mitigation | Contingency |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | AIS provider unavailable | High | High | disconnects, no messages, provider health failure | supervised connection, backoff/jitter, bounded subscription, health metrics, persisted required observations | label cache/gap; show unavailable; disable live layer |
| R-02 | AIS rate/connection limits exceeded | Medium | High | rejected fourth connection, frequent subscription close | centralize backend connection, respect three-connection and update limits, multiplex clients | narrow scope; queue subscription changes; reduce regions |
| R-03 | AIS pricing/terms change or use rights unclear | Medium | High | provider notice, unclear redistribution language | archive/review terms before integration/release; provider abstraction; minimize raw redistribution | pause affected feature; replace provider after review |
| R-04 | External API outage | High | Medium | timeouts/error-rate spike | provider-specific timeouts, retries, circuits, cache, isolated modules | serve labeled cache within TTL; `DATA UNAVAILABLE` |
| R-05 | Unexpected API costs | Medium | High | quota/budget alert | call accounting, caching, budgets, hard quotas, non-commercial/commercial decision | degrade polling/layers; disable source before overrun |
| R-06 | Large AIS volume overwhelms compute/storage | High | High | queue lag, memory/disk growth | bounded regions/types, batching, partitioning, retention, compression, profiling | shed nonessential updates; shorten retention; pause ingest |
| R-07 | WebGL performance is poor | High | Medium | low frame rate, high memory, context loss | clustering/LOD, instancing, route lazy-load, GPU profiling | reduced effects/2D fallback; visible aggregation |
| R-08 | Browser/GPU differences break rendering | Medium | Medium | browser-specific failures | capability detection, supported-browser matrix, fallbacks | disable unsupported layer/3D and provide table/2D path |
| R-09 | Data licensing/attribution breach | Medium | High | missing terms record/attribution | source gate, license inventory, UI attribution, release review | remove source/data/artifact until compliant |
| R-10 | Stale data appears current | Medium | High | ingestion lag exceeds threshold without warning | computed freshness, multiple timestamps, UI status contract, tests | force delayed/offline state; invalidate cache |
| R-11 | Time zone errors corrupt analysis | Medium | High | shifted buckets/playback | UTC storage, aware timestamps, explicit display zone, boundary tests | recompute affected results with new algorithm version |
| R-12 | Coordinate/CRS mistakes | Medium | High | points displaced, wrong distances/areas | EPSG:4326 boundary, SRID constraints, geography/projected metric queries, tests | quarantine/reimport; invalidate spatial derivatives |
| R-13 | Duplicate vessel records/messages | High | Medium | inflated counts, overlapping positions | fingerprints, idempotent writes, documented dedup windows, identity observations | rerun normalized/derived layers from raw manifests |
| R-14 | Missing or incorrect AIS fields | High | Medium | null/conflict rates rise | nullable schemas, quality flags, no inferred defaults, field-level provenance | hide/qualify fields; suppress dependent rules |
| R-15 | Network reconnect causes continuity gaps | High | High | disconnect and later event-time jump | record connection epochs/gaps, persist stream, show gap, no interpolation across gap | mark affected interval incomplete; exclude from claims |
| R-16 | WebSocket fan-out instability/slow clients | Medium | High | buffer growth, latency | bounded queues, coalescing, quotas, heartbeat, slow-client disconnect | reduce update frequency; require narrower filters |
| R-17 | PostGIS queries become slow | Medium | High | p95/plan regression | spatial/time indexes, bounded queries, partitioning, EXPLAIN baselines, aggregates | cancel/limit query; serve precomputed lower-resolution result |
| R-18 | Mobile layout becomes unusable | Medium | Medium | clipped panels/controls | progressive disclosure, device testing, simplified mobile modes | limit advanced workflow with clear desktop recommendation |
| R-19 | GitHub secret leakage | Medium | Critical | scanner alert or exposed key | `.gitignore`, server-only settings, push protection, secret scan, review | revoke/rotate immediately; incident review and history remediation |
| R-20 | Deployment cost exceeds solo budget | Medium | High | forecast/actual cost threshold | cost ceiling, retention plan, sleep/scale-to-zero where safe, budget alerts | reduce retention/features; take public demo offline safely |
| R-21 | MarineCadastre mistaken for global history | Medium | High | global labels or comparisons | explicit U.S.-water coverage in contracts/UI/docs | block global view; correct published claims/results |
| R-22 | AccessAIS ordering unavailable | High | Medium | official outage notice | use official bulk archives/manifests as primary ingestion path | postpone affected region/year; never scrape around controls |
| R-23 | Provider schema drift | Medium | High | contract fixture failure, unknown envelope | versioned adapters, drift monitoring, reject/quarantine breaking records | freeze last compatible source version; disable ingestion |
| R-24 | Port entity resolution merges wrong places | Medium | High | conflicting identifiers/coordinates | retain source records, identifier-first matching, confidence/manual review | unlink records; republish affected derivatives |
| R-25 | Anomaly false positives harm credibility | High | High | reviewer rejection/alert overload | explainable rules, quality-aware suppression, calibration, neutral language | disable rule; retract/recompute affected indicators |
| R-26 | Earthquake updates/retractions create inconsistency | Medium | Medium | provider `updated` changes | upsert by source ID/version, keep revision metadata | mark prior result superseded and recompute context |
| R-27 | Open-Meteo coastal/model values misused | Medium | High | users infer navigation precision | model/resolution/valid-time warning and attribution | disable sensitive presentation; clarify limitations |
| R-28 | One developer becomes bottleneck | High | High | growing WIP, stale docs, failing CI | narrow slices, WIP limit, automation, modular monolith, phase gates | reduce scope; delay advanced phases rather than cut quality |
| R-29 | Dependency sprawl and upgrades | Medium | Medium | duplicate libraries, large bundle, vulnerabilities | dependency justification, lockfiles, periodic review, adapters | remove/replace dependency; postpone feature |
| R-30 | Backups or migrations fail | Low | High | restore test failure | automated backups, migration tests, rehearsed restore and rollback | stop release; restore last verified snapshot |
| R-31 | Generated intelligence invents claims | High | High | uncited/unsupported output | delay to Phase 8, structured evidence, citations, evals, narrow use cases | disable intelligence feature; retain deterministic views |
| R-32 | UI aesthetics obscure uncertainty | Medium | High | status/attribution missed in usability test | evidence-first design review, restrained motion/glow, state matrix | simplify visuals; block release of misleading component |

## Top risks before Phase 1

1. Confirm AISStream terms for public display, caching, retention, and redistribution.
2. Select a bounded live geography and raw AIS retention policy.
3. Decide whether the public deployment is commercial; Open-Meteo free use is non-commercial.
4. Set a monthly hosting/storage budget ceiling.
5. Accept that initial historical analysis is U.S.-water only or fund/approve another global archive.

## Phase 2 entry review — 2026-09-17

- R-09 and R-23 are active source gates. Provider adapters cannot begin until current
  official terms, attribution, release identifiers, and schemas are reverified.
- R-10, R-11, and R-13 are addressed first through explicit source states, UTC-aware
  timestamps, versioned ingestion runs, quality counts, and idempotency keys.
- R-21 remains a hard scope boundary: MarineCadastre may support only bounded U.S.-water
  historical work and cannot justify global historical claims.
- R-24 is now mitigated at the source-record boundary: UN/LOCODE and WPI records are kept
  separate with their own immutable versions and keys. Canonical port matching remains
  deferred; no name-only merge is authorized.
- R-30 mitigation has started with a dedicated PostGIS upgrade/downgrade/upgrade test for
  the provenance migration. Backup and restore rehearsal remains a later release gate.
- The UN/LOCODE and WPI download/parse/persist paths have local real-data evidence. WPI
  redistribution remains `unreviewed`, and neither source has a public data route or
  production deployment. Other providers and cache policies remain unvalidated.
- R-26 now has an implemented first control: USGS events update only when the provider
  `updated` timestamp advances, while feed versions and raw artifacts remain traceable.
  Deletion/retraction polling and downstream recomputation remain future work.
- R-27 now has an implemented first control: bounded Open-Meteo imports preserve requested
  and selected-grid coordinates, UTC valid time, units, request parameters, checksums,
  raw artifacts, and model-data warnings. Public display, explicit cache-age policy, and
  model-resolution presentation remain future work.
- R-21 and R-22 now have an implemented first control: the MarineCadastre importer uses
  an official daily bulk archive, requires explicit U.S.-water spatial/time bounds and a
  record cap, preserves the raw checksum and requested scope, and reports truncation and
  archive/schema failures without implying global or complete receiver coverage.
- R-09, R-10, and R-32 now have a minimal UI control: the source-status surface reads the
  provenance APIs, shows textual controlled states, timestamps, current cache age,
  attribution, redistribution state, accepted/rejected counts, and quality issues. It
  returns `DATA UNAVAILABLE` on request failure and never substitutes placeholder values.
- R-18 has automated responsive CSS coverage but still needs manual browser/device visual
  review before the Phase 2 gate; the current automation environment exposed no browser.

## Phase 2 gate review - 2026-09-18

- R-09 remains an active release gate. Public record repositories require
  `redistribution_status = allowed`; WPI (`unreviewed`) and MarineCadastre AIS
  (`restricted`) cannot cross the public query boundary.
- R-10 now has tested per-provider freshness and maximum-cache policies. Status and record
  APIs share the same decision, label usable fallback `CACHED` with age, and return
  `DATA UNAVAILABLE` after expiry instead of presenting stale data as current.
- R-21 remains enforced in importer bounds, API scope, UI copy, and documentation. The
  stored MarineCadastre slice is described only as bounded U.S.-water historical data.
- R-22 is mitigated for the Phase 2 scope by the checksum-pinned official daily bulk
  archive path. AccessAIS ordering availability is not required by the implemented import.
- R-23 has schema/version checks, bounded downloads, typed adapters, rejection and quality
  reporting, and source-version pinning. A breaking provider response fails the run rather
  than entering production storage silently.
- R-18 retains one verification gap: automated component, responsive-style, TypeScript,
  and production-build checks pass, but a supported-browser visual review must be recorded
  before the Phase 2 gate closes.

## Review protocol

Each review updates likelihood, impact, evidence, mitigation status, owner, and next review date. A high-impact risk without an active mitigation blocks its dependent phase. Closed risks remain in history with the decision or evidence that closed them.
