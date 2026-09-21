# Development Roadmap

This roadmap is sequential at the gate level, not a promise of dates. Each phase may contain small vertical slices. A later phase starts only after its dependencies and acceptance evidence exist.

Current state on 2026-09-19: Phase 0, Phase 1, Phase 2, and Phase 3 are complete. Phase 4
Live AIS remains planned and requires a separate owner authorization. Developer A remains Project
Lead + Full-Stack GIS Engineer with about 65%-70% of the forward workload; Developer B is
Data & Platform Engineer with about 30%-35%. Existing Ownership Wins: stable modules are not
moved merely to fit the new responsibility table.

## Phase 0 — Research & Planning

**Status:** Complete; V2.1 retrospective complete. Do not redo.

**Objective:** Establish a credible, buildable product scope based on verified sources and the project's original single-developer constraints.

**Tasks:** Define charter, personas, use cases, non-goals, routes, architecture, source catalog, governance, UI direction, test/security strategy, GitHub plan, risks, skills, and completion gates. Record owner decisions still needed.

**Technical work:** Verify official endpoint documentation and terms; define provider boundaries, provenance envelope, freshness states, spatial/time standards, performance hypotheses, and ADR backlog. No application implementation.

**Files/modules expected:** `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`, and `docs/00` through `docs/12`.

**Dependencies:** Access to official provider documentation and repository-owner review.

**Potential risks:** Planning becoming speculative, incorrect global-coverage assumptions, stale terms, architecture overreach.

**Acceptance criteria:** Every requested document exists; six initial sources have official links, known limits and fallback policies; scope distinguishes planned from completed; open decisions are explicit.

**Definition of Done:** Documentation review passes, no business code or dependencies were introduced, and the owner approves entry to Phase 1.

## Phase 1 — Engineering Foundation

**Status:** Complete; continue focused engineering hardening without reinitialization.

**Objective:** Create the smallest professional foundation that supports repeatable development and later real-data slices.

**Tasks:** Initialize repository structure; record ADRs; configure Python/TypeScript projects, formatting, linting, type checks, tests, pre-commit policy if justified, Docker Compose, configuration loading, structured logging, error contracts, CI, and contributor commands.

**Technical work:** Establish modular backend/frontend boundaries, typed settings, secret validation, health skeletons, test factories that cannot enter production, migration tooling without domain-heavy schema, and dependency/license inventory.

**Files/modules expected:** `apps/web`, `apps/api`, `workers`, `packages` or equivalent shared areas, `infra`, `tests`, `scripts`, ADR directory, CI workflows, lockfiles, container definitions.

**Dependencies:** Phase 0 approval; choices for package managers, license, repository visibility, and supported OS/deployment target.

**Potential risks:** Boilerplate growth, incompatible GIS versions, slow CI, secrets in examples, premature abstractions.

**Acceptance criteria:** Clean checkout runs documented lint/type/test commands; minimal apps expose only health/dev shell; no fake production data path exists; dependency choices have reasons.

**Definition of Done:** CI is green, secret scanning is active, local setup is reproducible, ADRs reflect actual structure, and no planned feature is falsely marked complete.

## Phase 2 — Real Data Foundation

**Status:** Complete. The gate evidence is recorded in `docs/26-phase-2-gate-verification.md`.
Data Explorer, manual responsive visual review, `NO COVERAGE`, `MODEL DATA`, and refresh
scheduling remain explicit follow-up work rather than retroactive gate claims.

**Objective:** Prove end-to-end ingestion, provenance, quality, and source health before rich visualization.

**Tasks:** Implement source catalog and ingestion-run model; integrate one release-based port source, WPI, one bounded MarineCadastre sample/import, Open-Meteo, and USGS; add validation, caching, manifests, quality reports, and `/data`/`/system` APIs.

**Technical work:** Create PostGIS schema/migrations, repositories, provider adapters, source fixtures captured within terms, checksum/version handling, idempotent upserts, cache policies, structured metrics, and minimal data-status UI.

**Files/modules expected:** backend modules `provenance`, `ports`, `history`, `ocean`, `risk`, `system`; provider adapters; migrations; import commands; contract/integration tests; source attribution assets.

**Dependencies:** Phase 1; PostgreSQL/PostGIS and Redis; confirmed source terms; bounded sample datasets; deployment cost assumptions.

**Potential risks:** Archive size, schema drift, port entity-resolution errors, model attribution mistakes, rate-limit breaches.

**Acceptance criteria:** Each integrated record traces to source/version; invalid rows are counted/quarantined; cache states are visible; source outages produce cached/unavailable states; no production fixture leakage.

**Definition of Done:** A reviewer can run a bounded import, inspect quality/provenance, query real data, and reproduce it from a manifest.

## Phase 3 — Digital Earth

**Status:** Complete; final gate evidence is recorded in `docs/30-phase-3-gate-verification.md`.
The accepted delivery includes the contract-first 2D spatial workspace and focused Three.js
globe over real bounded data. Cesium and deck.gl remain conditional on requirements not
covered by the accepted globe and MapLibre adapter.

**Objective:** Deliver the map-first spatial shell using real port, marine, and hazard data.

**Tasks:** Implement responsive application shell, design tokens, 3D globe and 2D analytical map adapters, layer registry, port/environment/event layers, selection inspector, legends, attribution, camera/time state, and accessibility alternatives.

**Technical work:** Integrate CesiumJS, MapLibre, deck.gl only where each is justified; spatial query endpoints; viewport cancellation; clustering/tiling; route-based loading; reference-device profiling.

**Files/modules expected:** frontend geospatial platform, shared status components, `ports`, `ocean`, `risk`, and overview feature modules; visual/performance tests.

**Dependencies:** Phase 2 source APIs and provenance contract; map tile/terrain provider decision and terms.

**Potential risks:** WebGL/browser variation, bundle size, token conflicts, attribution overlap, inaccessible map-only workflows.

**Acceptance criteria:** Real layers render with source/freshness information; map interaction remains within agreed budgets; reduced-motion and lower-capability modes work; no page implies live AIS yet.

**Definition of Done:** Supported browsers pass functional, accessibility, and visual checks on reference hardware and the digital-earth slice is documented.

## Phase 4 — Live AIS

**Status:** Planned.

**Objective:** Add resilient, backend-mediated live vessel awareness with honest continuity and bounded load.

**Tasks:** Implement the Pelyr `/v1` worker, fixed subscription configuration, per-message licence/provenance mapping, position normalization, bounded in-memory latest-vessel state, same-origin product WebSocket fan-out, live map layers, vessel detail, reconnect behavior, backpressure, anti-extraction controls, and health telemetry. Search, tracks, export, and durable retention remain separate decisions.

**Technical work:** JSON frame validation, source/licence resolution, duplicate/stale-update handling, connection supervision, heartbeat/loss processing, client event coalescing, fixed-bound enforcement, replay-gap labeling, origin/rate controls, and load testing.

**Files/modules expected:** `live_ais` worker/provider and services, bounded in-memory latest state, same-origin WebSocket gateway, live/vessel frontend features, operational dashboards/runbooks. No repository or migration is required for the first slice.

**Dependencies:** Pelyr self-service account/key and key-backed smoke evidence; the reviewed Pelyr API Terms 1.5 and Data Licence 1.1; Phase 2 provenance; Phase 3 renderer; the fixed Gulf of Finland scope; zero-persistence policy; and explicit Phase 4 implementation authorization.

**Potential risks:** Private pilot with no upstream SLA/replay or global guarantee, changing mixed-source licences, disconnections, message bursts, stale positions, accidental data redistribution, identity conflicts, and key exposure.

**Acceptance criteria:** Key never reaches browser/logs; every displayed observation resolves to the current source directory and visible attribution; reconnect, heartbeat-loss, unknown-licence, and gap behavior are tested; live position exposes event/ingest time; load and extraction paths remain bounded; provider outage never creates positions.

**Definition of Done:** A measured region can run continuously through planned failure scenarios with documented data loss/continuity semantics and green integration/load tests.

## Phase 5 — Historical Analytics

**Status:** Planned; only the bounded internal U.S.-water importer exists today.

**Objective:** Provide reproducible U.S.-water historical playback and traffic analyses from MarineCadastre.

**Tasks:** Build archive registry/import jobs, partitioned storage, track segmentation, playback API/UI, density and traffic aggregates, vessel/area/time filters, charts, exports if approved, and reproducibility manifests.

**Technical work:** Stream/columnar ingest with Polars or DuckDB, year-specific schemas, spatial clipping, temporal bucketing, segment/gap rules, materialized aggregates, tile/LOD delivery, and benchmark datasets.

**Files/modules expected:** historical importer, dataset/analytic-run models, track and aggregation services, history/analytics UI, notebooks only if reproducible and noncanonical, result validation tests.

**Dependencies:** Phase 2 data contract; storage budget and retention; selected U.S. demo regions/years.

**Potential risks:** Multi-gigabyte files, disk/memory exhaustion, misleading message counts, missing fields across years, slow spatial queries.

**Acceptance criteria:** Coverage and denominator are visible; a known bounded dataset reproduces expected track/count summaries; imports are resumable/idempotent; playback discloses sampling.

**Definition of Done:** A documented historical scenario runs end-to-end from official archive checksum to map/chart conclusions within agreed resource budgets.

## Phase 6 — Risk & Anomaly Engine

**Status:** Planned.

**Objective:** Produce explainable rule-based indicators for review without overstating meaning.

**Tasks:** Implement geofences, entry/exit/dwell events, speed and course rules, AIS observation-gap detection, anomaly review states, earthquake proximity context, evidence panels, and rule-version management.

**Technical work:** Spatial predicates in PostGIS, time-window/state machines, circular-angle handling, gap/coverage logic, baseline calibration, false-positive evaluation, idempotent event generation, audit history.

**Files/modules expected:** risk domain, rule registry, event/evidence repository, batch/stream evaluators, risk frontend, calibration datasets and tests.

**Dependencies:** Phases 4–5 data; explicit thresholds/use cases; coverage-quality metrics.

**Potential risks:** False positives, confusion of missing coverage with behavior, threshold overfitting, alert fatigue, reputational harm.

**Acceptance criteria:** Every indicator shows rule/version/input window/evidence; boundary cases are tested; reprocessing is deterministic; language avoids intent or safety claims.

**Definition of Done:** Approved scenarios meet precision/false-positive review targets and all alerts are traceable, explainable, and retractable.

## Phase 7 — Advanced Visualization

**Status:** Planned.

**Objective:** Improve analytical depth and polish while preserving correctness and performance.

**Tasks:** Add GPU density/flow layers, multiscale route visualization, linked brushing, richer time controls, comparison views, carefully scoped camera transitions, and export-quality charts.

**Technical work:** deck.gl aggregation/instancing, server tiles/aggregates, worker/off-main-thread transforms, GPU capability detection, adaptive LOD, visual regression and performance budgets.

**Files/modules expected:** advanced layer implementations, visualization registry, export service where approved, performance harness, design documentation.

**Dependencies:** Stable Phase 3–6 semantics and representative load profiles.

**Potential risks:** Visual effects altering perceived values, GPU memory pressure, browser inconsistency, inaccessible interactions.

**Acceptance criteria:** Visual encodings match source calculations; fallback renderers preserve meaning; target interactions meet budgets; exports include provenance and units.

**Definition of Done:** Each visualization has a documented analytical question, encoding contract, validation test, accessible summary, and performance result.

## Phase 8 — Intelligence

**Status:** Research/planned after deterministic evidence products.

**Objective:** Add evidence-grounded assisted analysis only after deterministic data products are trustworthy.

**Tasks:** Define safe use cases, retrieval/evidence packaging, citation format, prompt/version governance, evaluation sets, refusal/uncertainty behavior, cost controls, and opt-in UI.

**Technical work:** Structured evidence API, model-provider abstraction if needed, grounding checks, output schemas, hallucination/citation evaluation, prompt-injection defenses for external text, observability and quotas.

**Files/modules expected:** intelligence service, evidence assembler, evaluation suite, prompt/version registry, safety notes, UI with citations and feedback.

**Dependencies:** Stable provenance and analytics; owner choice of provider, budget, privacy, and acceptable use.

**Potential risks:** Hallucination, stale evidence, untrusted source text, cost, latency, users treating summaries as operational advice.

**Acceptance criteria:** Claims link to evidence; unsupported requests are qualified/refused; evaluation thresholds pass; no secret/raw restricted data is sent without approval.

**Definition of Done:** A narrow approved workflow passes grounding, security, latency/cost, and human-review gates; broader claims remain out of scope.

## Phase 9 — QA & Security

**Status:** Planned release-candidate hardening; continuous checks already run earlier.

**Objective:** Harden the complete system against failures, regressions, abuse, and operational mistakes.

**Tasks:** Complete threat model, SAST/dependency/container/secret scans, authorization and rate-limit tests, fuzz/property tests, browser matrix, accessibility audit, load/soak/failure tests, backup/restore, incident and disaster runbooks.

**Technical work:** Fix findings, tighten headers/CORS/CSP, verify SQL parameterization and WebSocket controls, optimize PostGIS queries, test migrations/rollback, establish SLOs and alerts.

**Files/modules expected:** threat model, test reports, performance baselines, runbooks, release checklist, SBOM, security policy.

**Dependencies:** Feature freeze candidate; representative deployment environment and data volumes.

**Potential risks:** Late architectural defects, flaky E2E, unresolved dependency vulnerabilities, insufficient observability, untested restores.

**Acceptance criteria:** No open critical/high finding without explicit block; supported browsers and accessibility targets pass; backups restore; load/failure objectives pass; docs match behavior.

**Definition of Done:** Release candidate evidence is signed off against `docs/12-definition-of-done.md`, with remaining lower risks accepted and recorded.

## Phase 10 — Production Release

**Status:** Planned.

**Objective:** Publish a secure, truthful, maintainable first production release and repository presentation.

**Tasks:** Finalize license/attributions, environment and domain, deployment, monitoring, budget alerts, data/source notices, demo walkthrough, tagged release, changelog, screenshots, issue templates, and rollback plan.

**Technical work:** Production configuration validation, migrations, seed only reference catalogs, smoke tests, TLS/DNS/security headers, observability verification, backup schedule, release artifact/SBOM publication.

**Files/modules expected:** production deployment manifests, release notes, operational handbook, final README/media, `LICENSE`, `SECURITY.md`, citation/attribution files.

**Dependencies:** Phase 9 approval; hosting and cost decisions; all provider terms suitable for public deployment.

**Potential risks:** Secret leakage, unexpected traffic/cost, provider policy conflict, stale demo, rollback failure.

**Acceptance criteria:** Fresh deployment passes smoke/security/source-state checks; budgets and alerts work; public claims match actual coverage; rollback is rehearsed; repository health is complete.

**Definition of Done:** Version `v1.0.0` is tagged only after production verification, known limitations are public, monitoring ownership is clear, and no feature remains mislabeled as complete.

## Cross-phase controls

- Update the risk register and decision log at every gate.
- Add/adjust tests in the same change as behavior.
- Reverify provider documentation and terms before its integration and before release.
- Measure before splitting services or adding infrastructure.
- Keep Git history free of secrets and bulk external datasets.

## Two-developer phase ownership

| Phase | Developer A lead | Developer B independent ownership |
| --- | --- | --- |
| 2 follow-up | Data/System UI, Data Explorer, status components, contracts, map shell preparation | provider review, freshness/cache/health backend, region query, provider/API tests |
| 3 | Command Center, Cesium/MapLibre, camera, layers, Region Workspace, Source/Confidence UI | BBOX/viewport/PostGIS queries, region summary, provider health, backend tests |
| 4 | Vessel layer/detail/follow, source/coverage/attribution and connection UI | Pelyr `/v1` adapter, licence mapping, bounded latest state, same-origin WebSocket/backpressure |
| 5 | History/playback/traffic/corridor/compare UX and chart-map linking | archive pipeline, manifest, partition/track/aggregate/corridor computation |
| 6 | Risk Center, geofence/evidence/timeline/explanation/environment context UX | deterministic rules, evidence storage, versioning/recompute/calibration support |
| 7 | about 80%: GPU layers, particles, columns, scenes, tours, interaction and polish | server aggregation, optimized payloads, query/cache performance |
| 8 | evidence use cases, report/citation/refusal UX, integration and release | structured evidence backend, deterministic query assembly, telemetry/evaluation data |
