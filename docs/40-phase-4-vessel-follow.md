# Phase 4 Developer A: selected-vessel locate and follow

**Date:** 2026-11-11

**Branch:** `ui/live-ais-vessel-follow`, based on `main` at `937c5fe`.

**Status:** A-side implementation and isolated browser checks complete. Phase 4 stays
`Planned`; credential-backed regional acceptance and original-image runtime acceptance
are still separate gates. This branch does not merge or close issue #62 / PRs #64-65.

## Authorized slice

This implements the next unfinished A-owned interaction in the Phase 4 kickoff and
the Phase4Plus route: locate and follow a selected current observation in the existing
bounded 2D vessel layer. Changes stay in the frontend, a test-only browser check and
status/risk documentation. No provider, backend, public event contract, key handling,
dependency, migration, persistence, export or subscription-bound change is included.

The original user checkout and its uncommitted globe, stylesheet and Chinese project
documents were left untouched; work used a separate D-drive Git worktree.

## User behavior

1. Select an observation in the accessible list. If the globe is active, selection
   switches to the existing 2D map; there is no live AIS rendering on the 3D globe.
2. `定位船舶` centers the current displayable observation, zooming to at least level 7
   while preserving a closer zoom. Selection alone does not seize the camera.
3. `跟随船舶` explicitly starts following. New accepted coordinates update the center
   directly; no position interpolation, track history or camera animation is used.
4. `停止跟随` or manual camera movement stops follow. Keyboard buttons and drag/pan
   remain available, and `aria-pressed` plus text communicate follow state.
5. Lost transport, a gap, missing coverage, invalid/expired cache, out-of-bounds or expired
   observations remove the controls through the existing display guards. Silent expiry
   uses their existing 15-second timer. A selection change, new epoch or accepted
   replacement snapshot remounts the controls with follow off, including when gap and
   recovery events are batched into one browser render. Explicitly restart follow.

`snapshotSequence` is local reducer metadata recording the accepted snapshot baseline;
it is not a new server field and does not alter event acceptance. It lets a replacement
snapshot reset camera intent even when the stream epoch remains unchanged.

The compact controls stay above the map legend; on a narrow screen they also clear
the coordinate readout. Existing attribution, observation time, source state, coverage,
five-minute display rules and the 5,000-point cap are retained.

## Rendering defect found during acceptance

The installed MapLibre 6 implementation derives its default worker URL from the
module's sibling path (`src/util/web_worker.ts` in the installed package). Vite's
optimized/built module paths do not preserve that worker location. Before correction,
the real camera moved, but the GeoJSON source remained loading and no vessel point
could be hit-tested. Unit map mocks alone did not reveal this defect.

`MapWorkspace` now imports the installed `maplibre-gl-worker.mjs?worker&url` and passes
its bundled URL to `setWorkerUrl`. The production build emits a separate worker asset.
No CDN, dependency upgrade or external worker service is introduced. Development and
built-preview browsers both select a different list item, click the first point at the
real map center and confirm selection returns to that point. This requires actual
worker-driven GeoJSON rendering, rather than merely a working camera mock.

## Reproducible verification

Run the existing frontend gates from the repository root:

```powershell
npm run web:format:check
npm run web:lint
npm run web:test
npm run web:build
git diff --check
```

The committed browser checker uses the already installed Playwright dependency and
requires its Chromium browser. It creates isolated contexts, intercepts all product
HTTP/WebSocket traffic, blocks external requests, uses only the shared `TEST DATA`
fixture and a second test observation, and creates no provider connection. Do not
use its results as real-data coverage evidence.

For development, start the existing web server in one terminal:

```powershell
npm run dev --workspace @oceanscope/web -- --host localhost --port 5174 --strictPort
```

Then run in another terminal:

```powershell
node scripts/check_live_ais_follow_browser.cjs http://localhost:5174
```

After `npm run web:build`, separately start the production preview and check it:

```powershell
npm exec --workspace @oceanscope/web -- vite preview --host localhost --port 5175 --strictPort
# Run in a separate terminal while preview stays running:
node scripts/check_live_ais_follow_browser.cjs http://localhost:5175
```

Results recorded on 2026-11-11:

| Check | Result |
| --- | --- |
| Frontend tests | 53 passed, including 12 selected-camera cases and App list-to-2D selection wiring |
| Format, lint, TypeScript and production build | Passed; existing large-bundle warnings remain |
| Development browser | Chromium desktop 1440x1000 and narrow 390x844 passed |
| Built-preview browser | Same two sizes passed, including actual rendered-point selection |
| Browser behavior | Locate, updated-position following, manual pause, keyboard restart, gap/reset, silent expiry and reduced motion passed |
| Visual inspection | TEST DATA screenshots inspected; narrow-screen coordinate overlap corrected |
| Secrets and diff | Gitleaks redacted history and staged-diff scans passed; `git diff --check` passed |

Screenshots are labeled TEST DATA and written only to ignored `tmp/`. Basemap/API
unavailability in them is intentional interception, not live-provider outage evidence.
The checker never adds debug globals or modifies application source at runtime.

## Remaining gates

No real credential, vessel payload or regional coverage was used. Production-image
network/build acceptance for B6.3, a fixed Gulf of Finland credential-backed browser
session, and measured bounded burst/memory/rendering acceptance remain open. The
browser check is local Chromium coverage, not a full browser/device support matrix.
The feature does not authorize navigation, infer vessel identity/safety, expand
coverage, persist observations or begin historical analytics.
