# Codex Skills Plan

## Current supported mechanism

Verified on 2026-09-16 against the official OpenAI documentation:

- Skill guide: <https://developers.openai.com/codex/build-skills>
- Plugin guide: <https://developers.openai.com/codex/build-plugins>

A Skill is a directory containing required `SKILL.md` instructions/metadata and optional `scripts/`, `references/`, `assets/`, and `agents/openai.yaml`. Repository-scoped skills belong under `.agents/skills/<skill-name>/SKILL.md`. Codex can invoke them explicitly or match their `description` implicitly. Official guidance recommends focused skills, instruction-first design, explicit inputs/outputs, and testing trigger descriptions.

A Plugin is a distribution package that may combine skills, MCP servers, and optional UI. OceanScope should not create a plugin during planning. Start with repository-scoped skills after workflows have been exercised manually; consider a plugin only when the capabilities are stable and genuinely reusable outside this repository.

The current environment exposes the official `skill-creator`, so implementation should use it rather than deprecated installation patterns. **No project Skill is created in Phase 0; this file is specification only.**

## Proposed layout after approval

```text
.agents/
  skills/
    maritime-data-engineer/SKILL.md
    geospatial-frontend/SKILL.md
    oceanscope-ui-design/SKILL.md
    fastapi-postgis/SKILL.md
    data-provenance/SKILL.md
    testing-qa/SKILL.md
    security-review/SKILL.md
    github-maintainer/SKILL.md
```

Shared rules stay in `AGENTS.md`; skills should reference stable project docs rather than duplicate every rule.

## Skill specifications

### `maritime-data-engineer`

**Trigger:** integrating, updating, validating, or debugging AIS, UN/LOCODE, WPI, MarineCadastre, Open-Meteo Marine, or USGS data.

**Inputs:** official source URL/docs, intended use/coverage, sample payload/archive, target canonical schema, terms status.

**Workflow:** verify official docs; check terms/key/rate limits; profile schema; define provenance and validation; implement provider adapter/import; add sanitized fixtures, retry/cache/failure behavior, quality report, and source catalog update.

**Outputs:** provider/source contract, mapping, validation tests, ingestion evidence, updated data-source and risk docs.

**Guardrails:** never invent endpoints/fields; never put keys in clients; never broaden geographic coverage; do not silently coerce missing values.

### `geospatial-frontend`

**Trigger:** building or reviewing CesiumJS, MapLibre, deck.gl, GeoJSON, spatial interaction, layer performance, or coordinate behavior.

**Inputs:** analytical question, geometry/CRS, expected feature volume, zoom/time behavior, source/freshness contract, target devices.

**Workflow:** select renderer/layer; validate coordinate order/CRS/antimeridian; define LOD/picking/legend/attribution; implement adapter; profile GPU/CPU/memory; add fallback and accessibility summary.

**Outputs:** layer implementation/spec, performance evidence, tests, and documented degradation behavior.

**Guardrails:** do not alter values for aesthetics; do not load all map engines globally; do not hide sampling or attribution.

### `oceanscope-ui-design`

**Trigger:** designing or changing OceanScope layouts, components, motion, responsive behavior, or visual tokens.

**Inputs:** user question, route, data states, priority content, target breakpoints, accessibility constraints.

**Workflow:** apply design principles/tokens; map loading/empty/live/cached/delayed/offline; prototype desktop and narrow layouts; review hierarchy/contrast/motion; add component and visual tests.

**Outputs:** implementation-ready component contract or UI changes, screenshots, accessibility and state evidence.

**Guardrails:** no decorative KPI invention, constant blinking, excessive neon/glow, or redesign outside the task.

### `fastapi-postgis`

**Trigger:** adding backend endpoints, services, repositories, migrations, or spatial queries.

**Inputs:** use case, request/response contract, data owner, query bounds, transaction and performance needs.

**Workflow:** keep route thin; place orchestration in service and access in repository; choose geometry/geography and indexes deliberately; validate bounds; add migration, query-plan/integration tests, and error/provenance metadata.

**Outputs:** modular backend change, migrations, tests, API documentation, ADR when architecture changes.

**Guardrails:** parameterized SQL only; no business logic in routes; no premature service split; never measure meters in unprojected degrees.

### `data-provenance`

**Trigger:** adding any external or derived data surface, cache, KPI, export, or source-status behavior.

**Inputs:** source fields/timestamps/version, transformation, cache plan, freshness thresholds, output claim.

**Workflow:** map provenance contract; distinguish event/update/ingest/cache times; define LIVE/CACHED/DELAYED/OFFLINE; add trace and failure tests; review UI labels and attribution.

**Outputs:** provenance fields, source/run linkage, visible state, validation evidence.

**Guardrails:** block random/fake production values and unlabeled cache fallback; no KPI without denominator/unit/query.

### `testing-qa`

**Trigger:** planning tests, completing a feature, fixing a regression, or preparing a phase/release gate.

**Inputs:** changed behavior, risk, acceptance criteria, environments, fixtures.

**Workflow:** select static/unit/property/contract/integration/component/E2E/performance coverage; ensure fixtures are isolated; run required commands; summarize failures and evidence; update regression suite.

**Outputs:** tests, reports, reproducible commands, residual-risk note.

**Guardrails:** do not mark tasks complete with required checks failing; do not chase coverage percentage at the expense of behavior.

### `security-review`

**Trigger:** source integration, authentication, WebSocket/API exposure, dependencies, deployment, secrets, or release review.

**Inputs:** change/diff, trust boundaries, data/secrets, deployment context, threat model.

**Workflow:** review keys, CORS/origin, query bounds, rate limits, SQL/XSS/SSRF, WebSocket buffers, dependencies, CI permissions, logs, and incident path; add tests and prioritized findings.

**Outputs:** findings with severity/evidence/remediation, fixed tests where authorized, updated threat/risk docs.

**Guardrails:** never print secrets; distinguish exploitable findings from hardening suggestions; block critical/high release issues.

### `github-maintainer`

**Trigger:** updating README, issues, milestones, workflows, releases, repository health, or project status.

**Inputs:** current phase/status, intended audience, completed evidence, CI/release state.

**Workflow:** keep planned/completed claims accurate; create focused issues/milestones; preserve attribution; validate links; update release notes and roadmap; check repository health/security settings.

**Outputs:** truthful public documentation and maintainable GitHub metadata.

**Guardrails:** never expose secrets/data; never mark a feature complete without acceptance evidence; avoid badge/status theater.

## Shared Skill contract

Every Skill should:

1. Read `AGENTS.md` and only the relevant project docs.
2. State required inputs, explicit outputs, and non-goals.
3. Verify external documentation rather than recalling interfaces.
4. Preserve user changes and avoid unrelated redesign/refactoring.
5. Run relevant lint/type/tests before completion.
6. Update source/risk/decision documentation when facts change.
7. Report unresolved decisions instead of inventing them.

## Creation and validation order

1. After Phase 0 approval, create `data-provenance` and `testing-qa` first because they constrain all implementation.
2. Create `maritime-data-engineer` during the first Phase 2 vertical slice and validate against one static and one live-like source.
3. Create `fastapi-postgis` after ADR/schema conventions stabilize.
4. Create `geospatial-frontend` and `oceanscope-ui-design` while implementing the first real layer.
5. Create `security-review` before externally reachable live ingestion.
6. Create `github-maintainer` when issue/release workflows are active.

For each Skill, test prompts that should trigger, should not trigger, and should require explicit invocation. Start instruction-only; add deterministic scripts only for repeated validation or generation that cannot be safely described. Review duplicate guidance and context cost quarterly.

## Plugin decision gate

Consider a skills-only Plugin only after at least two skills are stable, useful across repositories, have representative evaluations, contain no OceanScope secrets/private assumptions, and have versioned documentation. Add an MCP server only for a real external-tool need with a security and maintenance owner.

