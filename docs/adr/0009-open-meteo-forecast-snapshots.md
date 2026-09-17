# ADR-0009: Bounded Open-Meteo marine forecast snapshots

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

OceanScope needs marine conditions before it has a map or public ocean API. Open-Meteo
provides numerical-model forecasts, not observations, and its free endpoint is limited to
non-commercial use. Coastal values, currents, tides, and sea level have documented
accuracy limits. An unbounded browser-driven grid would also make request volume and
provenance hard to control.

## Decision

- Use only the official Marine Weather API through a backend provider adapter.
- Limit one import to one WGS 84 coordinate and 1–168 forecast hours, in GMT/UTC, with
  `cell_selection=sea` and the verified `best_match` routing mode.
- Import seven explicit hourly variables: wave height, direction and period; sea-surface
  temperature; ocean-current velocity and direction; and mean-sea-level height.
- Preserve requested coordinates separately from the provider-selected grid coordinate,
  and store the latter as PostGIS geography SRID 4326.
- Preserve units, valid time, retrieval time, request parameters, response checksum, raw
  response artifact, normalization version, and row-level quality flags.
- Reject misaligned or truncated arrays, changed units, non-UTC responses, invalid
  coordinates, duplicate/non-increasing times, out-of-range values, and rows for which
  every requested value is null. Never replace missing values with zero.
- Store forecast snapshots by source version, request key, and valid time. The API does
  not expose a forecast issue timestamp, so the content checksum participates in the
  source version rather than inventing a model-run time.
- Treat `best_match` as a provider routing selection, not as the name of one underlying
  numerical model. Attribution therefore names Open-Meteo and refers to its documented
  underlying providers without claiming an unavailable per-value model identity.
- Keep this slice internal. It does not yet provide a public forecast route, scheduled
  refresh, cache fallback, or navigation guidance.

## Consequences

The importer is bounded, auditable, and safe against zero-fill or coordinate ambiguity.
Repeated processing of identical content is idempotent, while changed forecast content
is retained as a new source version. A later cache policy must select the newest usable
snapshot by request key, enforce an explicit age limit, and report `CACHED` or
`DATA UNAVAILABLE` rather than silently substituting values.

## Alternatives considered

- Browser calls for every visible map cell: rejected because request bounds, quota use,
  cache behavior, and attribution would be difficult to enforce.
- Store only the latest forecast: rejected because updates would not be reproducible.
- Label values as observations: rejected because the provider publishes model output.
- Infer a forecast issue time or exact underlying model: rejected because those fields
  are not present in the verified response contract.
