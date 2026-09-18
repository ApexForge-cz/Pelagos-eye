# Definition of Done

## Purpose

“Done” means the requested behavior is implemented, verified, documented, secure enough for its exposure, traceable to real data, and operable by either member of the two-developer team. It does not mean “code written” or “looks correct locally.”

For README and roadmap status, a feature is `Implemented` only when real data, backend,
frontend, error states, source display, tests, and documentation form one verified user
slice. Backend-only work is `Backend Ready`; UI-only work is `Prototype`; fixture-driven
work is `Development Only`; unbuilt work is `Planned` or `Research`.

## Universal task checklist

- Scope and acceptance criteria are satisfied; non-goals remain untouched.
- No unrelated redesign or dependency was introduced.
- Important logic has positive, negative, boundary, and failure tests.
- Required formatting, lint, type checks, tests, and builds pass.
- External-data paths include provenance, freshness, attribution, validation, and fallback behavior.
- No production path uses fake/random substitute values.
- Secrets are server-side, unlogged, uncommitted, and represented only by names in examples.
- Errors are observable and safe; user-visible state distinguishes empty from unavailable.
- Documentation, risk register, ADR/source catalog, and screenshots are updated when affected.
- Performance/accessibility/security impacts were checked in proportion to risk.
- The final report lists verification evidence and remaining limitations.

## Data-source integration Done

- Official docs and terms were reverified and linked with review date.
- Access/key, coverage, format, update behavior, limits/cost, fields, attribution, and fallback are documented.
- Provider adapter is isolated and has sanitized contract fixtures.
- Schema/range/time/coordinate/identifier validation is implemented.
- Source version, ingestion run, raw reference/checksum, timestamps, cache state, and quality flags are queryable.
- Retry/timeout/circuit/cache policies are bounded and tested.
- Outage and schema-drift behavior produces labeled cache or unavailable state.
- Public display/retention/redistribution is permitted or the feature is not released.

## Backend feature Done

- Transport layer is thin; business behavior lives in services; storage logic lives in repositories.
- Request and response contracts are typed and documented.
- Spatial operations use PostGIS with correct SRID/units and appropriate indexes.
- Queries are bounded, parameterized, paginated where needed, and measured for representative load.
- Migration applies from a clean and previous supported database; recovery/rollback is documented.
- Unit/integration/authorization/failure tests pass.

## Frontend feature Done

- Real APIs or explicitly isolated test fixtures drive all values.
- Loading, empty, live, cached, delayed, offline, and error states are handled.
- Source, effective time, freshness, units, coverage, and uncertainty are visible where relevant.
- Keyboard, focus, contrast, reduced motion, and responsive behavior pass the agreed target.
- Components are feature-scoped/modular; server state is not duplicated into an unrelated store.
- Visual regression and supported-browser checks pass.

## Geospatial layer Done

- Analytical question, source, CRS, coordinate order, units, legend, zoom/time behavior, and picking are documented.
- Geometry/antimeridian/boundary cases are tested.
- Feature volume, frame rate, memory, payload, and query performance meet agreed budgets on reference hardware.
- Clustering/downsampling/aggregation is disclosed and does not alter underlying values.
- Fallback/reduced capability preserves essential meaning.
- Attribution is visible and not obscured by controls.

## Analytics or anomaly Done

- Input dataset/version, spatial and temporal scope, denominator, units, algorithm/version, parameters, and run status are recorded.
- Result is reproducible from a checksum/manifests and code revision.
- Boundary, missing-data, coverage, and sensitivity cases are tested.
- Comparison inputs and constraints are consistent.
- Language matches evidence; anomaly does not imply intent, wrongdoing, collision, or emergency.
- UI links the result to supporting records and quality flags.

## Documentation Done

- Facts and links are current at the recorded review date.
- Planned, in-progress, and completed states are accurate.
- Commands and paths work from a clean checkout.
- Architecture diagrams match deployed components.
- No secret, personal information, internal-only path, or unlicensed large data is included.
- Link/spell/style checks pass where configured.

## Phase gate Done

- All phase acceptance criteria in the roadmap have evidence.
- Risks are reviewed; high-impact blockers are mitigated or the phase remains open.
- ADRs and source contracts reflect the implemented system.
- CI is green and no required job was silently skipped.
- Resource/cost and performance measurements are recorded.
- Known limitations and deferred work are explicit.
- The maintainer approves moving to the next phase.

## Phase 0 historical gate

- All requested planning files exist.
- At the original Phase 0 gate, README used a planning status and marked unfinished
  capabilities as planned. Current README must instead reflect the latest verified phase.
- Official source research corrects scope and avoids invented endpoints.
- Each Phase 0–10 has objective, tasks, technical work, expected files/modules, dependencies, risks, acceptance criteria, and definition of done.
- `AGENTS.md` contains the permanent engineering rules.
- `.env.example` contains names/comments only and no values.
- No application code, page, API, database, dependency installation, or bulk boilerplate was created.
