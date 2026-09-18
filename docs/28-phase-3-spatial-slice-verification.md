# Phase 3 first spatial slice verification

- Review date: 2026-09-18
- Branch: `gis/phase-3-digital-earth`
- Scope: first bounded 2D spatial slice only
- Slice status: accepted locally
- Phase 3 status: active, not complete

## Delivered contract

- The public port query accepts an all-or-none WGS 84 viewport and explicitly rejects
  antimeridian-spanning bounds until split-query support is designed.
- The web client issues bounded, cancellable port and past-24-hour earthquake queries with
  a 100-record cap per layer. Exact-coordinate marine queries use a bounded 24-hour window.
- Real stored UN/LOCODE ports render as projected MapLibre markers. Earthquake and marine
  failures retain their independent states; one unavailable provider does not suppress a
  usable layer.
- Selection details expose source state, source/effective time, attribution, cache age,
  data version, units, and quality flags where applicable.
- Empty exact-coordinate forecasts display `NO COVERAGE`; provider failures display
  `DATA UNAVAILABLE`. Neither state is converted to zero or generated records.
- A keyboard-operable viewport list exposes the same selectable record details without
  requiring direct map manipulation.
- OpenStreetMap raster tiles are optional presentation context. A two-second preflight
  prevents tile failure from blocking local WGS 84 grid and real-data rendering.

## Acceptance evidence

| Check | Result |
| --- | --- |
| Backend Ruff format and lint | Passed; 88 files formatted |
| Backend strict mypy | Passed; 80 source/test files |
| Current Linux backend suite | 87 passed, 1 skipped, 73% coverage |
| Port viewport tests | 8 passed on Windows; partial, inverted, and antimeridian bounds covered |
| Frontend Prettier and ESLint | Passed |
| Frontend Vitest | 2 files, 4 tests passed |
| Strict TypeScript and Vite build | Passed |
| Desktop browser inspection | Passed at 1440x900 in Microsoft Edge via Playwright |
| Mobile browser inspection | Passed at 390x844 in Microsoft Edge via Playwright |
| Real-data browser smoke | 100 of 1,479 matching ports rendered in the desktop viewport |
| Marker keyboard selection | Passed; selected Abbot Point and exposed live UNECE provenance |
| Offline/partial-source smoke | OSM shown as offline; USGS returned 503; ports remained usable |
| Production reverse-proxy contract | `/ports`, `/earthquakes`, and `/ocean/` added to Nginx |
| Gitleaks v8.28.0 | Passed; history and 3.49 MB filtered working tree scanned, no leaks found |
| `git diff --check` | Passed before this record; rerun at handoff |

The skipped backend test is the destructive migration round trip, which requires an
explicit disposable `OCEANSCOPE_TEST_DATABASE_URL`. The migration itself was unchanged by
this slice. The Windows full suite could not start asyncio's local socket pair in the
restricted host environment, so the current 88-test tree was copied to a temporary path in
the existing Linux API container and run there.

## Browser findings resolved during acceptance

1. MapLibre's library CSS overrode the map container height with its 300 px default. A
   higher-specificity container rule now fixes the canvas to the available map frame.
2. An external raster source in the initial style blocked viewport initialization when OSM
   was unreachable. The raster now attaches only after a bounded availability probe.
3. MapLibre GeoJSON worker loading remained stalled in the tested headless Edge runtime.
   The capped first slice now uses native projected DOM markers; high-volume rendering is
   still gated on later profiling.
4. The sticky mobile module dock obscured layer controls in the first full-page capture. It
   now remains in document flow on narrow viewports.

## Remaining limitations

- The MapLibre lazy chunk is approximately 1.04 MB minified (about 280 KB gzip); Vite emits
  its standard 500 KB chunk warning. Route-level GIS splitting remains a performance task.
- The accepted marker path is intentionally capped and is not evidence for live AIS or
  high-volume historical rendering.
- OSM tiles were unavailable in the acceptance environment. The offline grid and records
  rendered correctly, but online raster appearance still needs a supported-network pass.
- The stored USGS past-hour snapshot was outside its usable window and correctly returned
  503 during the smoke test, so no current earthquake marker was available to inspect.
- Marine forecasts remain stored exact-coordinate samples, not continuous ocean coverage.
- The Computer Use browser surface was unavailable; Playwright used the installed Microsoft
  Edge channel instead. Manual cross-browser and physical-device review remains open.
- Cesium 3D, deck.gl, live AIS, playback, analytics, risk inference, and production release
  remain outside this accepted slice.

## Decision

The first Phase 3 2D spatial slice satisfies its local acceptance contract and may serve as
the base for the next small Phase 3 increment. This decision does not mark Phase 3 complete
and does not authorize claims of global real-time coverage or production readiness.
