# Project Charter

## Identity and status

- Product: **OceanScope**
- Subtitle: **Global Maritime Situational Awareness & Analytics Platform**
- Chinese name: **全球港航态势感知与智能分析平台**
- Repository: `ApexForge-cz/Pelagos-eye`
- Stage: Phase 1 — Engineering Foundation
- Team: one developer
- Planning baseline: 2026-09-16

## Vision

Create a public, portfolio-grade maritime analytics platform that helps users understand where vessels are, how maritime traffic changes, what environmental conditions surround activity, and whether observable behavior warrants investigation. OceanScope will combine strong geospatial presentation with explicit provenance and uncertainty.

## Problem statement

Useful maritime context is distributed across sources with different schemas, geographic coverage, latency, reliability, licensing, and semantics. A compelling map can easily overstate what the data actually proves. OceanScope addresses both problems: it creates a coherent exploration experience and makes source health, timestamps, coverage, and limitations visible.

## Target users

- Maritime and GIS learners exploring real datasets
- Data engineers and analysts studying traffic patterns
- Port and logistics researchers needing public-source context
- Recruiters and open-source reviewers evaluating a substantial full-stack/GIS project
- Developers seeking a reproducible reference architecture for streaming and spatial data

OceanScope is not initially targeted at vessel operators, coast guards, emergency dispatchers, or regulated safety-critical workflows.

## Outcomes

1. A responsive map-first application backed only by traceable external data.
2. A replaceable provider architecture for live, historical, port, environmental, and hazard sources.
3. Reproducible historical analyses with consistent spatial and temporal rules.
4. Clearly bounded anomaly indicators that describe observations without claiming intent or causality.
5. A maintainable public repository that one developer can operate and explain.

## Scope

### In scope

- Global basemap and 3D globe experiences
- Live AIS ingestion from a server-side provider connection
- U.S.-water historical AIS analysis using MarineCadastre as the first verified archive
- Global port discovery using UN/LOCODE and NGA WPI
- Marine forecast/model overlays and earthquake context
- Vessel, port, route, track, geofence, traffic, trend, and health workflows
- Data lineage, freshness, caching, observability, tests, security, and documentation
- Later, evidence-grounded assisted summaries that cite their inputs

### Out of scope for the initial release

- Certified navigation, voyage planning, collision avoidance, or emergency response
- Guaranteed global historical AIS coverage
- Vessel ownership, sanctions, cargo, or commercial intelligence not supplied by verified sources
- Native mobile applications
- Multi-tenant enterprise administration, billing, or complex organization management
- Predictive claims about unlawful behavior or vessel intent
- A distributed microservice platform

## Product principles

1. Real data before impressive numbers.
2. Source truth and uncertainty are part of the interface.
3. The map is the primary workspace, not a decorative background.
4. Progressive detail beats permanent visual noise.
5. A modular monolith is the default until measured load justifies separation.
6. Compute once, cache deliberately, and disclose cache age.
7. No analytical claim without a reproducible path to source records.

## Success metrics

Targets are planning hypotheses and will be baselined with real measurements:

- 100% of external records expose required provenance metadata or a documented reason why a field is unavailable.
- 0 production paths create substitute random values.
- 100% of source-backed screens show status and freshness.
- Core API p95 latency under an agreed threshold for cached queries; thresholds set in Phase 1 load budgets.
- Stable interaction at a defined reference vessel count and reference GPU; budgets set after Phase 2 profiling.
- Reproducible ingestion and analytical fixtures in CI.
- All critical and high security findings resolved before public production.

## Constraints and assumptions

- One developer must be able to run the project locally with documented commands.
- External providers can fail, throttle, change schemas, or change terms.
- Live AIS completeness varies by receiver coverage and upstream conditions.
- MarineCadastre provides U.S. historical coverage and cannot substantiate a global-history claim.
- The public repository cannot contain credentials or redistributed datasets whose terms prohibit it.
- Cloud budget is limited and must be capped before persistent high-volume ingestion.

## Governance and decisions

Architecture-impacting choices use short ADRs beginning in Phase 1. Data-source onboarding requires a completed source contract, license note, fixture, validation rules, and rollback/fallback plan. Product changes that add a new external source must update the source catalog and risk register.

## Phase 0 exit gate

Phase 0 is complete when all requested planning documents exist, official data-source claims have citations, architecture and ownership boundaries are coherent, every phase has acceptance criteria, risks have owners and mitigations, and the repository owner has reviewed the open decisions. No business implementation is part of this gate.

**Gate result (2026-09-17): Complete.** The repository owner explicitly approved starting
Phases 0 and 1 and provided the public `ApexForge-cz/Pelagos-eye` repository. Its existing
MIT license is recorded in ADR-0005.
