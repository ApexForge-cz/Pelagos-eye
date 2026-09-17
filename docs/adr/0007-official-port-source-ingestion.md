# ADR-0007: Official port-source ingestion and source-record boundary

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

Phase 2 needs reproducible real data before a public map or canonical port catalog can be
trusted. UNECE UN/LOCODE and NGA World Port Index overlap, but they have different update
cycles, identifiers, coordinate precision, fields, and redistribution evidence. Merging
them during ingestion would hide conflicts and make later corrections difficult.

## Decision

Integrate the verified official UN/LOCODE release archive and WPI complete CSV behind
typed provider and parser contracts. Preserve each accepted row as a source record tied
to an immutable `source_version` and `ingestion_run`.

- Resolve UN/LOCODE from the official release API, pin the release tag, select only rows
  declaring port function `1`, and retain its coarse/optional coordinate semantics.
- Download WPI from the official complete-CSV endpoint. Because it exposes no reliable
  edition header, use the content SHA-256 as data version and header SHA-256 as schema
  version.
- Store bounded downloads as content-addressed local artifacts and keep bulk artifacts
  outside Git.
- Store WGS 84 points as PostGIS `geography(Point, 4326)` while retaining original raw
  fields, coordinate values, normalization version, and quality flags.
- Reject structurally invalid required fields or WPI coordinates; never replace them
  with zeroes or invented values. Retain UN/LOCODE rows with missing/coarse-invalid
  optional coordinates as nonspatial records with a quality flag.
- Make imports idempotent by source version, normalization version, and code revision.
- Keep UN/LOCODE and WPI source records separate. Canonical port entity resolution and
  public APIs require later evidence and decisions.
- Record WPI redistribution as `unreviewed`; downloaded WPI artifacts remain local until
  release-time terms review.

## Consequences

- Real port-reference data is reproducible from official URLs and checksums.
- Source conflicts remain visible and reversible instead of being hidden in an early
  merge.
- PostGIS supports later bounded spatial queries without treating degrees as meters.
- Some official rows are rejected or stored without geometry; quality counts are part of
  the successful run rather than silently repaired.
- A current WPI snapshot cannot be redistributed or exposed publicly merely because it
  was imported successfully.

## Alternatives considered

- Commit official bulk files to Git: rejected because snapshots change, enlarge history,
  and may have redistribution constraints.
- Merge by normalized name and country during ingestion: rejected because names and
  coordinates conflict and false merges would corrupt both sources.
- Use the WPI feature service as the bulk source: rejected because the official CSV is
  the documented complete content and avoids query pagination limits.
- Generate missing coordinates: rejected because production data may not be fabricated.
