# Phase 4 Developer A: bounded 2D vessel layer preparation

**Status:** A-side map adapter prepared on `gis/live-ais-bounded-vessel-layer`. Phase 4 remains `Planned`; there is no live vessel feed in the product UI yet.

**Scope:** `apps/web` only. No Pelyr key, browser-to-provider call, new endpoint, test position in production, or claim of live coverage.

The optional `MapWorkspace.liveAis` input accepts the v1 client reducer state plus a separate boolean for the current browser WebSocket connection. The MapLibre GeoJSON layer receives at most 5,000 latest positions and invokes `onVesselSelection` with the current normalized observation. It never draws a point when the transport is closed, continuity requires a new snapshot, the status is unavailable/disconnected, coverage is missing, or its observation is older than five minutes or outside the effective WGS 84 bounds. A 15-second timer removes expired points even when no new event arrives. The optional map label reports the source state, coverage, effective time, rendered observation count, truncation, and available per-source attribution; empty results are observations, not a claim that no vessels exist.

The existing Phase 3 page does not pass this optional input. B6.2 must first deliver and pass review for a same-origin, bounded gateway. A's next integration task must connect that gateway to the reducer, clear display on socket close/gap, provide an accessible non-map vessel list and selected-position details (including observation time, units, source and quality flags), and run end-to-end disconnect, stale, empty, and no-coverage checks. Do not turn on this layer in production or mark Phase 4 complete before those acceptance gates.

## Verification

- `npm run web:format:check`, `npm run web:lint`, `npm run web:test`, `npm run web:build`, `git diff --check`: run before handoff.
- Test-only shared v1 fixtures exercise the display guards; the map mock tests current-observation selection and empty updates. No fixture is imported into production code.
- No browser screenshot of live vessels is possible before the B6.2 gateway. The existing page does not pass AIS observations into the optional layer.
