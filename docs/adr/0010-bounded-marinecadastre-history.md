# ADR-0010: Bounded NOAA MarineCadastre historical AIS imports

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

MarineCadastre provides historical AIS observations for U.S. waters, not a global or live
feed. AccessAIS is currently unavailable, while NOAA directs users to daily bulk archives.
Those national archives are large, the 2026 republication uses Zstandard-compressed CSV,
and the FAQ documents receiver gaps, fallible vessel-entered fields, sentinel values, and
redistribution constraints.

## Decision

- Use the official NOAA daily bulk index and construct URLs only from an explicit UTC
  archive date in the verified 2015–2025 schema range.
- Require a WGS 84 box no larger than 5° by 5°, a UTC time window no longer than six
  hours within the archive date, and an explicit record cap no greater than 100,000.
- Stream downloads and Zstandard decompression with compressed-size and scanned-row
  limits; never expand the national archive fully in memory.
- Label a direct official download `LIVE`; label a checksummed local archive replay
  `CACHED` and record its age rather than presenting cached bytes as live retrieval.
- Support only the documented legacy column names and the verified 2026 snake-case
  aliases. Unknown schemas fail closed and retain a checksummed raw artifact for review.
- Preserve MMSI, observation time, point geometry, motion fields, selected static fields,
  raw row, normalization version, quality flags, archive date, request bounds, checksum,
  source URL, retrieval time, and code revision.
- Treat known SOG/COG/heading sentinels as missing. Invalid optional values become null
  with flags; invalid identifiers, times, or coordinates reject the row. Never zero-fill.
- Deduplicate exact source rows by a raw-record fingerprint. A record cap is disclosed as
  `coverage_unknown`; capped slices are not evidence of complete traffic or receiver
  coverage.
- Mark redistribution as restricted and keep the raw archive/internal record API private
  until release rights and presentation requirements are reviewed again.

## Consequences

The project can reproduce a real, spatially and temporally bounded historical slice without
claiming global history or loading a national day into PostGIS. A run still scans the daily
archive, so it is a batch operation rather than an interactive query. Public playback,
track construction, near-duplicate rules, retention policy, and performance budgets remain
future work.

## Alternatives considered

- AccessAIS orders: unavailable on the review date and unsuitable as the only reproducible
  path.
- Commit a sample archive: rejected because bulk data must not enter Git and redistribution
  remains restricted.
- Import an entire national day: rejected because it exceeds the Phase 2 bounded slice and
  has no demonstrated storage or query budget.
- Treat absence as vessel absence: rejected because NOAA documents receiver and archive
  coverage gaps.
