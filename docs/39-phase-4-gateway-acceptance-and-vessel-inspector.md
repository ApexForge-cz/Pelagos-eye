# Phase 4 gateway acceptance and Developer A vessel inspector

**Status:** Changes requested for merged PR #54. Real gateway-to-map integration is blocked by Issue #56. Phase 4 remains `Planned`.

**Review date:** 2026-10-08

## Developer B B6.2 acceptance

PR #54 merged the bounded in-memory latest state, loopback-development WebSocket gateway, optional worker lifecycle, tests, and load evidence. Its CI format, lint, type, test, build, and secret gates passed. Developer A's post-merge Bugbot review nevertheless found two P1 continuity races:

1. provider epoch changes and gaps clear latest/pending state but not queued ingress, so an old provider-session position may be published after a replacement snapshot or under the new product epoch;
2. slow-client recovery can reuse an event sequence while an earlier event is in flight, breaking strict monotonicity and potentially hiding the recovery gap.

Issue #56 assigns the follow-up scope to Developer B on `fix/live-ais-gateway-continuity`. The required regression tests cover queued ingress at epoch/gap boundaries and unique monotonic sequences during in-flight overflow recovery. Developer A will not connect the browser to the gateway until that focused PR passes review.

## Developer A independent progress

`LiveAisVesselInspector` prepares the selected-position and accessible non-map experience without opening a WebSocket or importing test fixtures into production:

- derives its list from the same continuity, connection, coverage, freshness, WGS 84 bounds, and five-minute expiry gates as the map layer;
- shows at most 100 keyboard-selectable observations while preserving the bounded full observation count;
- distinguishes `DATA UNAVAILABLE`, `FRESH SNAPSHOT REQUIRED`, `NO COVERAGE`, and an available covered region with zero current observations;
- hides selected details immediately when the observation is no longer displayable;
- presents MMSI as an AIS identity observation, UTC observation/ingest times, WGS 84 coordinates, knots/degrees, nullable fields, source state, attribution, and quality flags; and
- warns that AIS identity/dynamic fields are fallible and are not proof of intent, safety, or wrongdoing.

The component is not mounted in the current page, because the gateway acceptance gate is not satisfied. After Issue #56 is accepted, Developer A can add the fixed same-origin socket controller, feed the reducer, connect selection between map/list/detail, and run real disconnect, overflow, stale, empty, no-coverage, and attribution acceptance checks.
