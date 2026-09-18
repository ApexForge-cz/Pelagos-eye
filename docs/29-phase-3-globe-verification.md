# Phase 3 focused globe verification

- Review date: 2026-09-18
- Branch: `gis/phase-3-digital-earth`
- Scope: focused 3D-globe increment over the accepted spatial contracts
- Increment status: accepted locally
- Phase 3 status: active, not complete

## Reference analysis and renderer decision

The owner-supplied 110.4-second, 1280x592 HEVC reference was sampled across its timeline.
Its relevant behaviors are a dominant textured globe, slow rotation, camera zoom, a blue
atmospheric rim, luminous point/route treatment, country outlines and selection, and HUD
rails around the spatial surface. Its aviation counts, aircraft icons, routes, warnings,
national highlight, and dashboard totals are unverified demonstration content and were not
copied.

Three.js 0.186 was selected for this increment because the required surface is a focused
overview globe over existing point contracts. The slice does not require terrain, 3D Tiles,
or token-backed imagery. MapLibre remains the precision 2D and lower-capability adapter.
Cesium and deck.gl remain conditional on later measured requirements.

## Delivered behavior

- Desktop defaults to a lazy-loaded 3D globe; narrow viewports default to the accepted 2D
  map. An explicit segmented control switches modes without changing data contracts.
- The globe uses the same capped, bounded port and earthquake records as the 2D view.
  WGS 84 coordinates are projected onto the sphere; direct marker selection opens the
  existing provenance-aware inspector.
- Atmosphere, lighting, deterministic stars, boundary lines, and marker halos add depth.
  They do not encode routes, traffic, risk, coverage, or activity.
- Pointer input stops automatic rotation. `prefers-reduced-motion: reduce` disables
  automatic rotation at initialization.
- WebGL2 creation/capability failure explicitly returns to MapLibre and displays a fallback
  notice. The keyboard-operable record list remains available in both modes.
- NASA Visible Earth imagery and Natural Earth 1:110m boundaries are stored locally with
  attribution in `apps/web/public/assets/ATTRIBUTION.md`. They are visual context only.

## Acceptance evidence

| Check | Result |
| --- | --- |
| Prettier and ESLint | Passed |
| Vitest | 2 files, 5 tests passed; includes 3D mode switching and WebGL fallback state |
| Strict TypeScript and Vite build | Passed |
| Desktop browser inspection | Passed at 1440x900 in installed Microsoft Edge |
| Desktop canvas pixel check | 879x699; sampled values 1-255, mean 31.28; nonblank |
| Direct 3D marker selection | Passed; a visible real port marker selected `Aewol` and opened the inspector |
| 3D/2D mode switch | Passed; MapLibre remounted with its accessible map label |
| Mobile browser inspection | Passed at 390x844; defaults to 2D and can explicitly load 3D |
| Mobile canvas pixel check | 375x448; sampled values 1-255, mean 41.53; nonblank |
| Responsive overflow | No document-level horizontal overflow; module dock remains intentionally scrollable |
| Reduced motion | Browser media query maps to `data-motion=reduced`; normal mode maps to `animated` |
| Runtime console | No unexpected JavaScript or WebGL errors during final interaction smoke tests |
| Port viewport regression tests | 8 passed on Windows during final handoff |
| Backend Ruff and mypy | Passed for 80 source/test files during final handoff |
| Frontend handoff checks | Prettier, ESLint, 5 Vitest tests, and production build passed |
| `git diff --check` | Passed during final handoff |

The production build keeps renderers in separate lazy chunks. The Three.js globe chunk is
approximately 576 KB minified / 143 KB gzip. The existing MapLibre chunk remains about
1.04 MB minified / 280 KB gzip and continues to trigger Vite's 500 KB advisory.

The Windows full backend suite remains limited by the documented asyncio local-socket
restriction in the health tests. The current Linux full-suite evidence remains 87 passed
and 1 skipped; the Phase 3 port-query regression subset was rerun locally at handoff.

## Remaining limitations

- The globe renders at most the first 100 records returned by each bounded API. The UI
  discloses loaded versus matching totals and truncation; this is not a representative
  density layer or evidence of complete global coverage.
- The globe has no vessel positions, inferred routes, live traffic, risk output, terrain,
  bathymetry, 3D buildings, or time playback. Those capabilities remain in later phases.
- Natural Earth boundaries and NASA imagery are overview context, not navigational charts.
- Microsoft Edge is the locally verified reference browser. Firefox/Safari, integrated-GPU
  limits, context-loss recovery, and physical-device testing remain open.
- Visual smoke tests used the currently available real-data services. The USGS snapshot was
  outside its usable window and correctly remained `DATA UNAVAILABLE`.

## Decision

The focused Three.js globe satisfies the authorized second Phase 3 increment and may be
used as the overview adapter over the accepted data contracts. This does not mark all of
Phase 3 complete and does not authorize Phase 4 live AIS or fabricated route/traffic data.
