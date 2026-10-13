# Phase 4 gateway acceptance and Developer A vessel inspector

**Status:** B6.1/B6.2 backend accepted after PRs #59 and #61. Developer A browser integration is implemented and awaiting real-data/runtime acceptance. Phase 4 remains `Planned`.

**Review date:** 2026-10-13

## Developer B B6.2 acceptance

PR #54 merged the bounded in-memory latest state, loopback-development WebSocket gateway, optional worker lifecycle, tests, and load evidence. Developer A's post-merge review found two P1 continuity races and a later P2 recovery acknowledgement race:

1. provider epoch changes and gaps clear latest/pending state but not queued ingress, so an old provider-session position may be published after a replacement snapshot or under the new product epoch;
2. slow-client recovery can reuse an event sequence while an earlier event is in flight, breaking strict monotonicity and potentially hiding the recovery gap.
3. an older replacement snapshot acknowledgement can clear a newer client recovery before its own snapshot is sent.

PR #59 fixed the two P1 races with ingress generations and in-flight-aware sequence allocation. PR #61 bound recovery completion to the exact replacement snapshot sequence and fixed the P2 race. Their backend, frontend, and secret-scan CI gates passed; the latest full backend evidence is 203 passed with one explicitly configured PostGIS integration skip. Issues #44 and #52 are accepted and closed. Real browser evidence remains a separate Developer A gate.

## Developer A independent progress

The browser integration opens one same-origin product WebSocket and feeds only validated v1 events into the continuity reducer. It does not import test fixtures into production. The mounted UI:

- derives its list from the same continuity, connection, coverage, freshness, WGS 84 bounds, and five-minute expiry gates as the map layer;
- shows at most 100 keyboard-selectable observations while preserving the bounded full observation count;
- distinguishes `DATA UNAVAILABLE`, `FRESH SNAPSHOT REQUIRED`, `NO COVERAGE`, and an available covered region with zero current observations;
- hides selected details immediately when the observation is no longer displayable;
- presents MMSI as an AIS identity observation, UTC observation/ingest times, WGS 84 coordinates, knots/degrees, nullable fields, source state, attribution, and quality flags; and
- warns that AIS identity/dynamic fields are fallible and are not proof of intent, safety, or wrongdoing.
- exposes transport disconnection as `DATA UNAVAILABLE` instead of retaining a stale server `AVAILABLE` claim;
- hides all positions until a fresh accepted snapshot restores continuity; and
- rejects malformed event-specific payloads before they can reach the reducer.

The first slice renders vessels in the 2D MapLibre workspace; the 3D globe does not yet have a live-vessel layer. Reconnection is explicit through the page refresh control rather than an unbounded browser retry loop.

## Remaining acceptance boundary

- Issue #62 must pass the Pelyr key/Origin Compose wiring and Nginx WebSocket proxy without exposing a credential.
- Run a credential-backed browser session against only the fixed Gulf of Finland box.
- Record snapshot-first ordering, status/coverage/attribution, vessel selection, disconnect, gap, stale expiry, empty coverage, and no-key behavior without committing vessel identifiers or coordinates.
- Recheck memory and browser rendering under bounded burst conditions.
- Keep production fail-closed until authentication, proxy topology, traffic limits, and release policy are accepted.

Until those checks pass, Phase 4 remains `Planned`; the UI may truthfully show `DATA UNAVAILABLE` and makes no global, complete, navigational, or production-availability claim.
