# Risk Register

Scales: likelihood and impact are `Low`, `Medium`, or `High` (`Critical` is retained for
security impact). Developer A is accountable for product/architecture/release risks;
Developer B is accountable for assigned data/platform controls. Review at every phase gate
and after source, architecture, team, or deployment changes.

| ID | Risk | Likelihood | Impact | Early indicator | Mitigation | Contingency |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | AIS provider unavailable | High | High | disconnects, no messages, provider health failure | supervised connection, backoff/jitter, bounded subscription, health metrics, persisted required observations | label cache/gap; show unavailable; disable live layer |
| R-02 | AIS rate/connection limits exceeded | Medium | High | rejected third connection, subscription close, changed `welcome.limits` | centralize one backend connection, enforce effective runtime limits, multiplex bounded clients | narrow scope; stop subscription changes; reduce clients/regions |
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
| R-20 | Deployment cost exceeds project budget | Medium | High | forecast/actual cost threshold | cost ceiling, retention plan, sleep/scale-to-zero where safe, budget alerts | reduce retention/features; take public demo offline safely |
| R-21 | MarineCadastre mistaken for global history | Medium | High | global labels or comparisons | explicit U.S.-water coverage in contracts/UI/docs | block global view; correct published claims/results |
| R-22 | AccessAIS ordering unavailable | High | Medium | official outage notice | use official bulk archives/manifests as primary ingestion path | postpone affected region/year; never scrape around controls |
| R-23 | Provider schema drift | Medium | High | contract fixture failure, unknown envelope | versioned adapters, drift monitoring, reject/quarantine breaking records | freeze last compatible source version; disable ingestion |
| R-24 | Port entity resolution merges wrong places | Medium | High | conflicting identifiers/coordinates | retain source records, identifier-first matching, confidence/manual review | unlink records; republish affected derivatives |
| R-25 | Anomaly false positives harm credibility | High | High | reviewer rejection/alert overload | explainable rules, quality-aware suppression, calibration, neutral language | disable rule; retract/recompute affected indicators |
| R-26 | Earthquake updates/retractions create inconsistency | Medium | Medium | provider `updated` changes | upsert by source ID/version, keep revision metadata | mark prior result superseded and recompute context |
| R-27 | Open-Meteo coastal/model values misused | Medium | High | users infer navigation precision | model/resolution/valid-time warning and attribution | disable sensitive presentation; clarify limitations |
| R-28 | Knowledge or ownership bottleneck | Medium | High | growing WIP, stale docs, unavailable owner | explicit ownership, runbooks, small PRs, cross-review, modular monolith | transfer with contract/evidence; reduce scope rather than cut quality |
| R-29 | Dependency sprawl and upgrades | Medium | Medium | duplicate libraries, large bundle, vulnerabilities | dependency justification, lockfiles, periodic review, adapters | remove/replace dependency; postpone feature |
| R-30 | Backups or migrations fail | Low | High | restore test failure | automated backups, migration tests, rehearsed restore and rollback | stop release; restore last verified snapshot |
| R-31 | Generated intelligence invents claims | High | High | uncited/unsupported output | delay to Phase 8, structured evidence, citations, evals, narrow use cases | disable intelligence feature; retain deterministic views |
| R-32 | UI aesthetics obscure uncertainty | Medium | High | status/attribution missed in usability test | evidence-first design review, restrained motion/glow, state matrix | simplify visuals; block release of misleading component |
| R-33 | Merge conflicts delay delivery | Medium | Medium | both developers edit shared files or migrations | path ownership, short branches, small PRs, serialized migrations | stop and rebase the smaller PR; split shared change |
| R-34 | Frontend/backend contract drift | Medium | High | fixture and API response differ | contract-first PR, typed schemas, contract tests, versioned changes | block integration and restore last agreed contract |
| R-35 | Duplicate implementation | Medium | Medium | parallel modules solve the same use case | issue owner, Existing Ownership Wins, architecture review | keep validated owner module; remove duplicate in focused PR |
| R-36 | New developer onboarding gap | Medium | Medium | repeated environment or domain misunderstandings | module map, runbook, starter issue, paired contract review | narrow scope and pair on first provider/platform slice |
| R-37 | Codex modifies unrelated files | Medium | High | broad diff or owner-boundary breach | AGENTS rules, allowed/forbidden paths, status/diff review | stop work; isolate intended patch without reverting user changes |
| R-38 | Concurrent migration conflict | Medium | High | multiple Alembic heads | one migration author at a time; A creates/reviews final migration | serialize PRs and reconcile with a reviewed merge migration only if needed |
| R-39 | No coverage presented as zero | High | High | empty map/KPI without coverage state | `NO COVERAGE` contract, coverage metadata, UI and test matrix | suppress metric; show coverage reason and source state |

## Top risks before Phase 1

1. Verify a self-service Pelyr key, effective limits, source directory, attribution, and bounded coverage without recording the secret or raw payloads.
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
- R-18 retains one non-blocking follow-up: automated component, responsive-style,
  TypeScript, production-build, Compose, and HTTP checks passed, but a supported-browser
  manual responsive visual review remains outstanding after the Phase 2 gate.

## Phase 3 first spatial slice review - 2026-09-18

- R-07 is bounded by a 100-record API cap per rendered layer. The accepted slice uses
  MapLibre DOM markers for this low-volume path after headless Edge exposed a GeoJSON-worker
  stall; deck.gl and high-volume rendering remain outside the slice and require profiling.
- R-08 has a tested lower-capability path: external OpenStreetMap tiles are probed with a
  short timeout and cannot block viewport or real-data rendering. Failure displays
  `BASEMAP OFFLINE · WGS 84` over a local coordinate grid.
- The second Phase 3 increment addresses R-07/R-08 with a lazy Three.js chunk, a WebGL2
  capability gate, desktop 3D/mobile 2D defaults, an explicit 3D/2D control, and automatic
  fallback to the accepted MapLibre path. Reference-browser canvas screenshots and pixel
  variance checks are recorded in `docs/29-phase-3-globe-verification.md`; cross-browser
  GPU coverage remains open.
- R-18 was inspected at 1440x900 and 390x844 in Playwright-driven Microsoft Edge. The
  mobile module dock was moved into document flow after the first inspection found it
  obscuring layer controls; the repeated screenshots show no remaining overlap or clipping.
- R-39 now has automated `NO COVERAGE` coverage for an empty exact-coordinate marine
  forecast. Provider failure remains `DATA UNAVAILABLE`, and viewport totals distinguish
  records loaded from records matched.

## Phase 4 contract entry review - 2026-09-19

- R-01, R-02, and R-03 remain hard entry gates. The current provider documentation and
  applicable display, cache, retention, redistribution, attribution, connection, and rate
  terms must be reverified before provider code or public live-data claims are authorized.
- R-10 and R-39 now have a proposed client contract that keeps source state, availability,
  coverage, cache age, and empty observations distinct. No route currently serves this
  contract, so this is design evidence rather than acceptance evidence for live data.
- R-14 is addressed in the proposal by nullable AIS fields, explicit units/ranges, and quality
  flags. Provider sentinel values must normalize to `null`; identity/static fields remain
  fallible observations.
- R-15 and R-16 now have proposed epoch, sequence, status, and gap semantics. The contract
  explicitly disallows replay claims, but reconnect, queue, coalescing, and slow-client limits
  remain unresolved and block implementation acceptance.
- R-19 remains unchanged: a future AISStream key must stay in server-only typed settings and
  must never enter browser bundles, public events, logs, fixtures, or committed files.
- R-34 is reduced by mirrored Python and TypeScript v1 shapes plus focused validation tests.
  Cross-language fixtures and an implemented route/gateway are still required before the
  contract can move from proposed to accepted.

## Phase 4 provider verification review - 2026-09-19

- R-01, R-02, R-03, and R-09 remain blocking. Official AISStream GitHub repositories
  provide pinned technical evidence for the WebSocket endpoint, subscription envelope,
  compression example, and message models, but the provider documentation and terms
  pages returned a Cloudflare `403` challenge during review.
- Historical issue #25 language about “no restrictions” is retained only as historical
  evidence and is not treated as a current license or redistribution grant. Current
  questions about public display, caching, storage, retention, commercial use, and
  downstream reuse remain unanswered for release purposes.
- The provider-neutral client contract remains design evidence. Do not add a provider
  adapter, live connection, API key, raw fixture, route, worker, or public live-data
  claim until the current terms are archived and the source gate is approved.

## Phase 4 browser verification follow-up - 2026-09-20

- R-02 is no longer blocked on discovering the published limits. A human browser review
  confirmed three subscribed connections per account, three pre-authentication open
  connections per originating IP, a three-second initial-subscription deadline, one
  replacement per connection per second, and 200 MMSI values per subscription. Runtime
  enforcement, continuous-read behavior, compression, queue bounds, and load evidence
  remain required controls.
- The documentation warns that slow consumers can lose buffered messages and that, from
  September 2026, uncompressed connections are bandwidth-limited per user with excess
  messages dropped. R-15 and R-16 therefore remain active and require explicit gap
  events; no completeness claim is permitted.
- R-03 and R-09 remain hard entry gates. The official terms page and its source rendered
  only garbled text in the human browser, so public display, caching, storage, retention,
  commercial use, redistribution, and attribution rights remain unverified.
- Written clarification is now tracked in official AISStream issue #298. Opening the
  request is evidence of escalation, not a grant; R-03 and R-09 remain blocking until
  the provider supplies an applicable, authoritative answer.

## Phase 4 bounded operating policy - 2026-09-20

- R-02 and R-06 now have an owner-approved planning boundary: one fixed New York Harbor
  box, `PositionReport` only, one backend provider connection, zero persistent live AIS
  storage, no track tails, and explicit queue/state/client ceilings. These controls still
  require load evidence and do not authorize provider access.
- R-10 is bounded by a five-minute in-memory latest-position expiry and explicit cache age.
  This cache remains disabled unless provider rights permit it; otherwise the design must
  be revised rather than serving unlabeled or unauthorized stale data.
- R-15 and R-16 now have proposed reconnect, epoch, snapshot, bounded-queue, coalescing,
  slow-client, and gap behavior. Overflow cannot be silent, replay remains unavailable,
  and positions cannot be interpolated across gaps.
- R-19 retains a zero-trust credential boundary: one server-only secret path, no browser
  provider access, and no raw payload or credential values in logs, metrics, fixtures, or
  public events.
- R-03 and R-09 remain hard blockers through official AISStream issue #298. The approved
  scope and budgets are planning decisions, not permission or Phase 4 completion evidence.

## Phase 4 provider replacement review - 2026-09-22

- R-03 and R-09 are reduced by the recorded Pelyr API Terms 1.5 and Pelyr Data Licence
  1.1. Bounded in-product display, storage, analysis, derived results, and commercial use
  are permitted with visible source-specific attribution. Pelyr-licensed position data may
  not be redistributed, exported, relayed, or offered through a data API.
- R-01 remains high because Pelyr is a private pilot with no SLA, global-coverage promise,
  or continuity guarantee. Fintraffic and Norwegian open AIS are candidates for separately
  reviewed direct-source fallback adapters; provider abstraction and `DATA UNAVAILABLE`
  behavior remain mandatory.
- R-02 now uses the effective `/v1` `welcome.limits` values rather than hard-coded
  AISStream limits. The first slice uses one connection and one fixed Gulf of Finland box.
- R-09 requires dynamic provenance. Every provider frame's licence id must resolve against
  the connection's source directory, and every represented attribution must remain visible.
  An unknown id stops publication and forces a source-directory refresh/reconnect.
- R-15 and R-16 use Pelyr heartbeats and loss counters as upstream evidence, while retaining
  OceanScope epoch, sequence, bounded queues, gap events, coalescing, and slow-client rules.
- R-19 applies to the self-service Pelyr key: it remains server-only and must not appear in
  URLs, browser code, logs, fixtures, screenshots, documents, or Git history.
- R-03, R-09, and R-19 still block implementation until Developer A completes a no-payload
  credential smoke check and accepts the effective limits, source directory, attribution,
  observed coverage, and same-origin anti-extraction controls. Phase 4 remains `Planned`.

## Review protocol

Each review updates likelihood, impact, evidence, mitigation status, owner, and next review date. A high-impact risk without an active mitigation blocks its dependent phase. Closed risks remain in history with the decision or evidence that closed them.
