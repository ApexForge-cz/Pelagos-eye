# OceanScope Agent Instructions

These rules apply to all work in this repository. Read the relevant planning documents before implementation. The current project status in `README.md` controls which phase is authorized.

OceanScope started as a single-developer project. Developer A remains Project Lead and
primary owner of product, architecture, frontend, GIS, integration, and release. Developer B
is Data & Platform Engineer and owns meaningful provider, ingestion, data-platform,
infrastructure, and backend-test modules. This history and ownership split must not be
rewritten as an equal 50/50 allocation.

## Permanent rules

1. Never fabricate production data.
2. Never expose API keys.
3. Prefer official APIs and datasets.
4. Validate external API documentation before integration.
5. Maintain data provenance.
6. Add tests for important business logic.
7. Run lint, type checks, and tests before marking a task complete.
8. Keep frontend components modular.
9. Keep FastAPI routes thin.
10. Business logic belongs in services.
11. Database access belongs in repositories or the data layer.
12. Use PostGIS for spatial operations.
13. Do not mix aviation terminology into maritime modules.
14. Do not redesign unrelated parts of the project.
15. Do not introduce dependencies without justification.
16. Avoid over-engineering.
17. Optimize large map layers for performance.
18. Every external-data UI must expose freshness information.
19. Cached data must be labeled.
20. Never silently fall back to fake values.
21. Real data comes before impressive numbers or visual decoration.
22. Existing ownership wins; do not move stable modules merely to make a responsibility table tidy.
23. Define or update typed contracts before parallel frontend/backend implementation.
24. Use small, focused pull requests and never push directly to `main`.
25. Do not modify another owner's module without an issue, agreed scope, and review.
26. Do not run repository-wide formatting in a feature pull request.
27. Never commit a secret, raw restricted dataset, database volume, or local cache.
28. Map and chart visualizations must not distort positions, values, units, uncertainty, or coverage.
29. Model output must be labeled `MODEL DATA`; derived output must be labeled `DERIVED`.
30. `NO COVERAGE` is not zero, no vessel, or `DATA UNAVAILABLE`.

## Data and source rules

- A provider failure may return a valid, age-labeled cache within policy or `DATA UNAVAILABLE`; it may not return invented, random, zero-filled, or unrelated values.
- Test fixtures must live in test-only paths, be labeled `TEST DATA`, and be impossible to import into production configuration.
- Synthetic performance records must be labeled `SYNTHETIC BENCHMARK` and isolated from production storage.
- Preserve source, source URL/reference, source/event/update time, ingestion time, cache state, schema/data version, and quality flags.
- Reverify official terms, limits, schema, and attribution before integrating or releasing a source.
- Do not claim global historical AIS coverage from MarineCadastre; its planned use is U.S. waters.
- Treat AIS identity/static fields and preliminary event data as fallible observations.
- Production code must not use `Math.random()`, generated records, test fixtures, zeros, or
  unrelated providers as a fallback for missing external data.

## Architecture rules

- Default to a clean-ish modular monolith. Split a service only with measured scaling, isolation, or ownership evidence.
- Follow API/handler → service → repository/provider boundaries.
- External providers must be behind explicit adapters and typed canonical contracts; do not leak raw provider dictionaries through the application.
- Use UTC internally, explicit time zones at presentation boundaries, and WGS 84 at source boundaries.
- Use an appropriate projection or PostGIS geography for metric calculations; never treat degrees as meters.
- Require spatial/time bounds for expensive queries and document aggregation/downsampling.

## UX and claims

- Use `LIVE`, `CACHED`, `DELAYED`, and `OFFLINE` as source states. Use `NO COVERAGE`,
  `MODEL DATA`, `DERIVED`, and `TEST DATA` as distinct coverage/content labels; do not mix
  them into the source-state enum. Always pair color with text.
- Distinguish empty results from unavailable data.
- Show units, coverage, effective time, source, and warnings beside the values they qualify.
- Anomalies are indicators for review, not proof of intent, wrongdoing, collision, or emergency.
- Preserve a calm, map-first dark maritime interface; avoid constant flashing, ticker decoration, excessive neon/glow, and effects that obscure data.
- Respect accessibility, responsive behavior, and reduced-motion preferences.

## Change discipline

- Stay within the authorized phase. Do not begin later-phase implementation without explicit user approval.
- Preserve user-authored changes and inspect the worktree before editing.
- Update tests and relevant source, risk, ADR, and public-status documentation in the same change.
- Record the commands/checks run and any remaining limitations.
- Never mark a planned capability completed without acceptance evidence.

## Collaboration and Git discipline

- Developer A primary paths: `apps/web`, UI, GIS/map, visualization, core API contracts,
  architecture, integration, README/demo/release.
- Developer B primary paths: providers, ingestion/workers, data pipelines, backend data
  operations, infrastructure, provider/backend tests, and performance pipelines.
- Shared paths include contracts, migrations, root configuration, GitHub files, README, and
  `AGENTS.md`; change them in independent small pull requests where practical.
- Do not create Alembic migrations concurrently. Developer B may propose a schema change;
  Developer A creates or reviews the final migration.
- Use short-lived functional branches such as `ui/*`, `gis/*`, `api/*`, `data/*`, `ais/*`,
  `history/*`, `risk/*`, `infra/*`, `test/*`, `docs/*`, `contract/*`, and `fix/*`.
- Before work, read `AGENTS.md`, the current branch/status, issue scope, allowed paths, and
  forbidden paths. Before handoff, run relevant format, lint, type, test, build,
  `git diff --check`, and configured secret checks, then report limitations.
