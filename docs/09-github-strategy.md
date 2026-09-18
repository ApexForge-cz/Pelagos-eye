# GitHub Strategy

## Repository intent

The repository should demonstrate disciplined product engineering, data correctness, and geospatial depth without pretending the product is complete. Public communication must keep status labels accurate.

## Recommended repository settings

- Visibility: public when Phase 0 content has been reviewed for personal information and terms.
- Default branch: `main`, protected once CI exists.
- Merge method: squash merge for focused pull requests; retain meaningful PR descriptions.
- Require pull requests, owner review, and required checks for both developers.
- Enable secret scanning, push protection, dependency alerts, and automated security updates with review.
- Disable unused features until there is a maintenance plan.

## Branch and commit model

- Short-lived functional branches: `ui/*`, `gis/*`, `api/*`, `data/*`, `ais/*`,
  `history/*`, `risk/*`, `infra/*`, `test/*`, `docs/*`, `contract/*`, and `fix/*`.
- Do not use long-lived `developer-a` or `developer-b` branches and do not push directly to `main`.
- One coherent outcome per pull request.
- Conventional-style commit subjects are recommended but not a release blocker.
- Never commit raw bulk datasets, credentials, local caches, database volumes, or generated build output.
- Architectural or provider changes include updated ADR/source/risk documentation in the same PR.
- Do not run repository-wide formatting, rename broad directory trees, or refactor another
  owner's module as incidental work.

## Ownership and conflict control

- Developer A owns product direction, architecture, `apps/web`, UI/GIS/map work, core API
  contracts, integration, README/demo, and release.
- Developer B owns new providers, ingestion/workers, data pipelines, backend data
  operations, infrastructure, provider/backend tests, and performance pipelines.
- Existing Ownership Wins: already stable modules keep their current owner.
- Contracts, migrations, root configuration, README, AGENTS, and GitHub files are shared;
  prefer separate small pull requests and explicit review.
- Only one developer creates a database migration at a time. Developer B may propose a
  schema change; Developer A creates or reviews the final Alembic migration.
- Contract-first development allows A to use isolated `DEV DATA` fixtures while B builds
  the same backend contract. Production uses real APIs only.

## Milestones

Create one milestone per roadmap phase after owner approval:

1. `Phase 0 — Research & Planning`
2. `Phase 1 — Engineering Foundation`
3. `Phase 2 — Real Data Foundation`
4. `Phase 3 — Digital Earth`
5. `Phase 4 — Live AIS`
6. `Phase 5 — Historical Analytics`
7. `Phase 6 — Risk & Anomaly Engine`
8. `Phase 7 — Advanced Visualization`
9. `Phase 8 — Intelligence`
10. `Phase 9 — QA & Security`
11. `Phase 10 — Production Release`

Milestones contain issues that produce testable artifacts, not duplicated prose from the roadmap.

## Labels

| Group | Labels |
| --- | --- |
| Type | `type:feature`, `type:bug`, `type:docs`, `type:research`, `type:security`, `type:data` |
| Area | `area:web`, `area:api`, `area:gis`, `area:ingestion`, `area:database`, `area:infra`, `area:ux` |
| Source | `source:aisstream`, `source:marinecadastre`, `source:unlocode`, `source:wpi`, `source:open-meteo`, `source:usgs` |
| Priority | `priority:critical`, `priority:high`, `priority:medium`, `priority:low` |
| State | `status:blocked`, `status:needs-decision`, `status:needs-validation`, `good-first-issue` |
| Risk | `risk:data-integrity`, `risk:performance`, `risk:license`, `risk:cost` |

Keep labels limited and documented; avoid overlapping synonyms.

## Issue templates planned

- **Feature:** problem, user outcome, scope/non-scope, data source, UX states, security/performance, acceptance evidence.
- **Data source:** official URLs, key/access, format, coverage, schema, terms, freshness, validation, fallback, attribution.
- **Bug/data incident:** observed behavior, affected time/source/version, reproduction, integrity impact, cache/publication impact.
- **Decision:** context, options, consequences, deadline/owner.

## Pull request template planned

Each PR records outcome, linked issue, screenshots for UI, data/source impact, migrations, tests run, performance/security impact, documentation changes, and rollback. A checkbox alone is not evidence; include commands/reports where useful.

## Projects and planning

Use a simple board: `Backlog` → `Ready` → `In progress` → `Review` → `Done`, plus a blocked field/reason. Limit each developer to one major slice and one small maintenance item; mark owner, contract, allowed paths, and dependency before work starts.

## CI/CD plan

### Pull request

- Markdown/link/style checks where reliable
- Ruff, mypy policy, ESLint, Prettier check, strict TypeScript
- Unit, contract, component, migration smoke tests
- Secret scan, dependency review, license policy
- Build minimal frontend/backend artifacts

### Main/nightly

- Integration and browser E2E
- PostGIS query regression and bounded performance jobs
- Optional protected live-provider smoke tests
- Container build and scan

### Release

- Full quality/security suite
- SBOM and provenance for artifacts
- Controlled deployment with environment protection
- Migration, smoke, source-health and rollback checks

Pin third-party actions to immutable commits. Give workflow tokens minimum permissions. Forked pull requests do not receive secrets.

## Releases and versioning

- `0.x` releases may mark stable development demonstrations; `1.0.0` requires the Phase 10 gate.
- Use semantic versioning for application contracts where meaningful.
- Generate release notes from curated changes, not raw commit lists.
- Every release states data-source coverage, known limitations, migration notes, and whether a live deployment exists.
- Never call a planning snapshot a production release.

## Repository health files, phased

Phase 0: `README.md`, `AGENTS.md`, `.gitignore`, `.env.example`, planning docs.  
Phase 1: `CONTRIBUTING.md`, issue/PR templates, ADR template, code of conduct decision, CI, dependency policy.  
Before public deployment: `LICENSE`, `SECURITY.md`, `CITATION.cff`, `CHANGELOG.md`, attribution/third-party notices, operations docs.

## README presentation plan

- Keep status and coverage above the fold.
- Add screenshots only when they show real implemented behavior.
- Keep planned/completed labels synchronized with releases.
- Add an architecture diagram and reproducible demo instructions after implementation exists.
- State costs/keys and source limitations plainly.

## Community posture

Until maintenance capacity exists, label the project as a personal project welcoming focused issues rather than promising response times. Security reports should use private reporting once enabled. Data-correction reports must include source and observation time and must not expose sensitive information.
