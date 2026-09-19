# Phase 3 Digital Earth gate verification

- Review date: 2026-09-19
- Scope: Phase 3 bounded 2D spatial workspace and focused 3D-globe increments
- Phase 3 status: complete
- Phase 4 status: planned; not authorized by this record

## Gate decision

Phase 3 satisfies its documented acceptance contract. The delivered workspace renders
bounded real port, earthquake, and marine-forecast data through the Phase 2 contracts,
provides MapLibre 2D and Three.js 3D modes with explicit fallback behavior, preserves
source and coverage semantics, and exposes an accessible record-list alternative.

This gate does not claim live AIS, global real-time coverage, route inference, risk
inference, navigational-chart capability, or production deployment.

## Evidence

| Check                                       | Result                                                                                                       |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Backend format, lint, and strict mypy       | Passed in CI; local Windows substitute also passed                                                           |
| Backend tests                               | Linux CI passed; local Windows run excluding the documented ASGI socket tests: 82 passed, 1 skipped          |
| Frontend Prettier and ESLint                | Passed                                                                                                       |
| Frontend Vitest                             | 2 files, 5 tests passed                                                                                      |
| Strict TypeScript and Vite production build | Passed                                                                                                       |
| Secret scan                                 | Passed in CI                                                                                                 |
| Edge desktop rendering                      | Passed at 1440x900; nonblank 3D canvas and no document overflow                                              |
| Edge mobile rendering                       | Passed at 390x844; 2D default, no document overflow                                                          |
| Firefox desktop/mobile rendering            | Passed through Playwright screenshots; 3D desktop and 2D mobile rendered real port markers                   |
| 3D/2D mode switching                        | Passed in desktop and mobile checks                                                                          |
| Real-data browser smoke                     | API `READY`; 100 of 11,798 matching ports rendered with truncation disclosed                                 |
| Port selection and provenance               | Passed; selected record exposed WGS 84 coordinates, `LIVE`, data version, source time, and UNECE attribution |
| Provider outage semantics                   | Passed; stale USGS snapshot returned `DATA UNAVAILABLE`/503 without fabricated events                        |
| Normal rotation                             | Passed; presentation rotation is visibly measurable and approximately two minutes per turn                   |
| Interaction recovery                        | Passed; drag/zoom pauses rotation and automatic rotation resumes four seconds after interaction ends         |
| Reduced motion                              | Passed; `prefers-reduced-motion: reduce` keeps the globe stationary                                          |
| WebGL fallback                              | Passed; capability failure returns to the 2D map and keeps the record list available                         |
| `git diff --check`                          | Passed                                                                                                       |

## Known limitations carried forward

- The spatial response and globe renderer are capped at 100 records per layer; this is not a density layer or complete global coverage claim.
- The globe has no live vessel positions, inferred routes, risk output, terrain, bathymetry, 3D buildings, or time playback.
- Natural Earth boundaries and NASA Visible Earth imagery are overview context, not navigational charts.
- OSM tile availability, USGS freshness, and marine forecast coverage depend on external provider state.
- Safari, physical-device GPU variation, WebGL context-loss recovery, and production deployment remain follow-up work.
- The local Compose image rebuild encountered a transient npm registry TLS reset; the current source passed CI build checks and the existing local runtime served real data successfully.

## Phase 4 entry conditions

Phase 4 remains `Planned`. Before Live AIS implementation begins, the project still needs
an approved AISStream account and terms review, a geographic demo scope, retention and
redistribution decisions, typed live-message contracts, and an explicit owner authorization
for the new phase. No Phase 4 provider, worker, WebSocket, vessel layer, or live-data claim
is introduced by this gate.
