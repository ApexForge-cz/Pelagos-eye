# ADR-0008: USGS feed versioning and latest-event revision semantics

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

The USGS real-time GeoJSON feed is regenerated every minute, while individual earthquake
events may be reviewed and revised after first publication. Treating every feed row as a
new event would inflate counts; overwriting without version provenance would make changes
irreproducible.

## Decision

- Ingest the official all-earthquakes past-hour GeoJSON feed as a bounded Phase 2 source.
- Identify each immutable feed snapshot by its `metadata.generated` value plus a content
  SHA-256 prefix, while retaining the full checksum and raw artifact.
- Keep one latest `earthquake_event` observation per stable USGS event ID.
- Replace an observation only when its provider `updated` timestamp is strictly newer.
  Count equal timestamps as unchanged and older timestamps as stale arrivals.
- Keep event time, provider update time, feed generation time, retrieval time, and
  normalization time separate.
- Store longitude/latitude as PostGIS geography SRID 4326 and depth as an explicit
  kilometre field, not as a 2D map altitude.
- Preserve the raw feature and provider status. Treat `tsunami` as provider metadata,
  never as an OceanScope forecast, emergency declaration, or impact assessment.
- Do not expose event records publicly in this slice.

## Consequences

Minute-level polling does not duplicate unchanged events, while every processed feed is
auditable. Later map/risk products can recompute from explicit revisions, but deletion and
retraction handling still requires a dedicated policy.

## Alternatives considered

- Append every feed feature: rejected because repeated hourly-window observations would
  inflate the event table.
- Overwrite by event ID without comparing `updated`: rejected because late feeds could
  revert reviewed information.
- Use FDSN custom queries for polling: rejected because USGS recommends real-time feeds
  for automated display and availability.
