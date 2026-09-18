# Data Governance

## Policy statement

OceanScope must never present fabricated, randomly generated, or silently substituted production data. Data quality, provenance, coverage, freshness, uncertainty, and provider state are product features and release gates.

## Environments and data classes

| Class | Allowed use | Required label |
| --- | --- | --- |
| Production external data | product screens and published analysis | source and freshness state |
| Cached production data | temporary continuity within approved stale window | `CACHED` plus age/source time |
| Derived production data | KPIs, tracks, aggregates, anomalies | input versions and algorithm version |
| Test fixture | automated tests and isolated story/demo tests | `TEST DATA`; never production routes |
| Synthetic benchmark data | performance/load tests only | `SYNTHETIC BENCHMARK`; isolated storage |
| Sample documentation data | explanatory snippets | `EXAMPLE`; not presented as current |

## Provenance contract

Every external record or derived dataset must carry or resolve to:

- `source_id` and human-readable source name
- `source_url` or stable dataset/event reference
- `source_record_id` when available
- `source_timestamp` / event or forecast valid time
- `source_updated_at` when supplied
- `ingested_at`
- `normalized_at` or transformation run reference
- `data_version` and `schema_version`
- `is_cached` and cache retrieval/age metadata
- `quality_flags`
- raw artifact/message reference or checksum when retention permits

Derived outputs additionally require algorithm name/version, parameters, input dataset versions, run timestamp, code revision, spatial/temporal scope, unit/denominator, and completion status.

## Freshness policy

Freshness thresholds are configured per source and data product after observed behavior is measured. Status is computed, never manually decorated:

- `LIVE`: latest acceptable record/run is inside its normal freshness objective.
- `CACHED`: response came from a verified cache; cache age is always visible.
- `DELAYED`: provider/ingestion is reachable but effective data exceeds the warning threshold.
- `OFFLINE`: source is unreachable or no cache remains inside the maximum stale window.

Forecast validity, event occurrence, provider update, ingestion, and display refresh are different timestamps and must remain distinct.

## Validation layers

1. **Transport:** status code/frame integrity, payload size, compression, content type.
2. **Schema:** required envelope, supported message/version, parsable values.
3. **Semantic:** coordinate/range checks, identifier patterns, time plausibility, enum handling, unit mapping.
4. **Relational:** source identity, duplicate detection, referential consistency.
5. **Spatial/temporal:** CRS, antimeridian, ordering, gaps, impossible jumps, stale/future timestamps.
6. **Analytical:** denominator, window, aggregation, conservation/invariant checks, reproducible result.

Invalid records are quarantined or rejected with reason counts. They are never coerced into plausible-looking defaults.

## Identity rules

- MMSI is an observed transponder identity and can be reassigned or malformed; it is not a timeless hull key.
- IMO identifier, call sign, name, dimensions, type, destination, and status may be missing or inconsistently broadcast.
- Vessel identity is modeled as time-aware observations with source confidence, not blind overwrites.
- Port entity resolution uses authoritative identifiers and geography; name-only joins are candidates requiring validation.

## Quality flags

Planned controlled flags include `missing_required`, `invalid_coordinate`, `invalid_timestamp`, `out_of_range`, `unknown_enum`, `duplicate`, `late_arrival`, `stale`, `identity_conflict`, `implausible_motion`, `coverage_unknown`, and `provider_revision`. Flags remain queryable and summarized in ingestion reports.

## Retention and minimization

- Retain only data required for documented features and reproducibility.
- Raw live AIS retention is an explicit owner/cost/terms decision, not unlimited by default.
- Large historical downloads are tracked by manifest and checksum; Git must not contain bulk data.
- Define hot, warm, archive, and deletion windows after Phase 2 volume measurements.
- Purge secrets and sensitive request details from logs; coordinates requested by users should not be retained without purpose.

## Reproducibility

- Pin release identifiers and checksums for static datasets.
- Record provider query parameters and model names for fetched products.
- Store code revision, configuration hash, and random seed for analytical procedures that use randomness.
- Keep immutable result manifests and constraint/quality summaries.
- Re-running the same versioned inputs should produce equivalent outputs within documented numeric tolerances.

## Attribution and licensing

- The source catalog stores license/terms URL, attribution text, allowed uses, redistribution status, and review date.
- User-facing views display required attribution without hiding it in repository documentation.
- A source with unclear retention or redistribution rights cannot be mirrored publicly until reviewed.
- Changes to provider terms trigger a source review and may disable ingestion or publication.

## Failure behavior

1. Retry only transient failures with bounded exponential backoff and jitter.
2. If valid cached data is within the approved window, serve it as `CACHED` with original times.
3. If data exceeds the window, show `DELAYED` or `OFFLINE` according to source state.
4. Display `DATA UNAVAILABLE` when no acceptable record exists.
5. Never catch an error and replace a value with a random number, zero, an old unlabeled value, or an unrelated provider value.

## Ownership and audit

Developer A is accountable for product claims, architecture, public contracts, and release
decisions. Developer B is primary steward for new providers, ingestion, validation, data
quality, platform operations, and backend evidence. Existing Ownership Wins: stable modules
already implemented by Developer A do not move solely to match the new responsibility table.
Each source has a catalog entry, review date, validation owner, and incident notes. Material
transformations require pull-request review or recorded checklist evidence.

## Governance release gates

- No production page without a source/status model.
- No KPI without a documented query, unit, denominator, and validation test.
- No source without terms/attribution review.
- No analytics result without a run manifest.
- No cache path without an age label and expiry rule.
- No public release while test/synthetic records can reach production queries.
