# Phase 3 Digital Earth kickoff

- Authorization date: 2026-09-18
- Working branch: `gis/phase-3-digital-earth`
- Phase status: active
- Lead owner: Developer A

## Authorized objective

Deliver the map-first spatial shell over real Phase 2 data without weakening provenance,
freshness, coverage, accessibility, or redistribution controls. Phase 3 began with a
bounded 2D vertical slice. That slice passed local acceptance, and the owner authorized a
second 3D-globe increment on 2026-09-18 after reviewing a supplied visual reference.

## First vertical slice

The first slice covers:

1. A responsive application shell with a dominant 2D spatial workspace.
2. Typed viewport and result contracts for public UN/LOCODE, USGS earthquake, and stored
   Open-Meteo marine-forecast data.
3. Bounded, cancellable queries driven by the visible WGS 84 viewport and explicit time
   windows where required.
4. Port and earthquake map layers plus an exact-coordinate marine forecast inspection
   workflow; the UI must not imply continuous ocean coverage from point samples.
5. Layer visibility, legends, selection details, attribution, source state, effective time,
   cache age, content labels, and quality warnings beside the data they qualify.
6. Loading, empty, `NO COVERAGE`, `DATA UNAVAILABLE`, and error states with an accessible
   non-map result representation.
7. Automated contract, service, component, accessibility-oriented, and production-build
   checks, followed by desktop and mobile browser inspection.

## Contract decisions before rendering

- WGS 84 longitude and latitude remain source-boundary coordinates.
- Viewport queries require bounded west, south, east, and north values. Antimeridian
  behavior must be explicit rather than inferred.
- Results are capped and disclose truncation or aggregation; an empty covered result is not
  `NO COVERAGE`.
- External-data responses preserve source/version, source time, ingestion time, update
  time, cache state, schema/data version, and quality flags where available.
- `LIVE`, `CACHED`, `DELAYED`, and `OFFLINE` remain source states. `NO COVERAGE`,
  `MODEL DATA`, `DERIVED`, and `TEST DATA` remain separate content/coverage labels.
- Restricted WPI and MarineCadastre records remain excluded from public record APIs.

## Explicitly outside the first slice

- Live AIS, vessel search, vessel tracks, or WebSocket delivery
- Historical AIS playback and traffic aggregation
- Canonical UN/LOCODE-to-WPI entity resolution
- Cesium globe acceptance, terrain, 3D buildings, or deck.gl high-volume layers
- Risk or anomaly assertions derived from earthquake proximity
- Production deployment or claims of global real-time coverage

## Authorized second increment: 3D globe

The supplied reference video is used only for interaction and visual-language analysis.
Its useful patterns are a dominant textured globe, slow camera motion, an atmospheric rim,
restrained luminous selection, depth-separated HUD rails, and globe-to-region inspection.
Its aviation labels, routes, counts, alerts, national highlight, ornamental telemetry, and
other unverified values are not copied.

The 3D increment covers:

1. A lazy-loaded Three.js globe adapter beside the accepted MapLibre adapter, selected by
   an explicit 3D/2D segmented control.
2. A local, attributable Earth texture and low-resolution public-domain boundary asset;
   runtime rendering must not depend on a private imagery token.
3. WGS 84 projection of the same bounded real port and earthquake records used by the 2D
   view, with click/tap selection feeding the existing evidence inspector.
4. Restrained atmosphere, marker halo, lighting, auto-rotation, and camera easing. These
   effects may establish depth but may not imply routes, movement, risk, or coverage.
5. User input immediately stops automated rotation. `prefers-reduced-motion` disables
   continuous motion, and lower-capability or failed WebGL paths return to the 2D adapter.
6. Desktop and mobile visual inspection, canvas nonblank/pixel-variance checks, interaction
   smoke tests, and production bundle measurement.

Three.js is selected instead of CesiumJS for this increment because the required surface is
a bounded overview globe over existing point contracts, without terrain, 3D Tiles, or an
external token-backed imagery stack. This keeps the adapter focused and permits the exact
atmosphere and marker treatment observed in the reference. Cesium remains a future option
only if measured requirements add terrain, tiled global imagery, or precision camera
behavior that the focused adapter cannot meet.

The 3D globe does not authorize live AIS, inferred vessel routes, animated traffic flows,
country-level risk highlighting, fabricated dashboard totals, or operational alerts.

### Second-increment acceptance evidence

- The globe renders nonblank on the reference desktop browser and preserves a usable 2D
  fallback on mobile and simulated WebGL failure.
- Port and earthquake coordinates map to the sphere without changing their values, and a
  selected point opens the same provenance-aware inspector as its 2D/list representation.
- Rotation, zoom, resize, cleanup, and reduced-motion behavior are verified; no animation
  continues after the component unmounts.
- Earth/boundary attribution is visible, and data-layer attribution remains in the existing
  inspector and source lens.
- Format, lint, strict type checks, focused tests, production build, browser screenshots,
  canvas pixel checks, `git diff --check`, and configured secret checks pass.

## Acceptance evidence

The slice is accepted only when:

- real stored records render through the public APIs with source and freshness information;
- viewport/time limits, cancellation, empty results, unavailable data, and redistribution
  gates have tests;
- keyboard users can inspect the same essential facts outside direct map manipulation;
- reduced-motion and lower-capability paths preserve meaning;
- reference desktop and mobile screenshots show no overlap, clipping, hidden attribution,
  or unreadable labels;
- format, lint, strict type checks, tests, production builds, `git diff --check`, and the
  configured secret checks pass; and
- the verification record reports measured limitations without marking all of Phase 3
  complete.

## Risk controls

This slice directly tracks R-07 (WebGL performance), R-08 (browser/GPU variation), R-18
(responsive layout), and R-39 (`NO COVERAGE` presented as zero). The 2D-first sequence
reduces renderer uncertainty while preserving a clear adapter boundary for later Cesium or
deck.gl evaluation.
