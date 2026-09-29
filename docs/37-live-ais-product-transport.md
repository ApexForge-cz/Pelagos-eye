# Phase 4 product transport decision (Developer A proposal)

**Status:** Proposed for B6.2 issue review. Phase 4 remains `Planned`.

The first slice transports only the frozen provider-neutral v1 event contract from
`apps/api/src/oceanscope_api/api/contracts/live_ais.py`. A client opens one
same-origin WebSocket at `/live-ais/ws` and receives a `vessel.snapshot` before any
incremental event. There is no separate public snapshot GET endpoint, URL-supplied
MMSI, bounding box, provider credential, resume cursor, replay, or export.

## Browser and gateway boundary

- The browser derives `ws://` or `wss://` from its current origin and uses only the
  fixed path. For local Vite development, proxy `/live-ais` to the API with WebSocket
  forwarding; this is still a browser-to-product connection, never a Pelyr connection.
- Before accepting a WebSocket, the API verifies `Origin` against an explicitly
  configured product-origin allowlist. Missing, `null`, or unapproved origins are
  rejected. Do not equate the existing CORS setting with WebSocket protection.
- An Origin header is not authentication: non-browser clients can forge it. Until a
  product session and extraction limits have been reviewed, enable this route only
  for loopback development; fail closed in production. In particular, do not offer
  an anonymously reachable public vessel feed. Developer A reviews the session,
  deployment/proxy topology, and traffic limits before public deployment.
- Do not start a Pelyr worker for every browser connection. One server-side worker
  serves at most the approved 25 local demo clients. When the key is absent,
  snapshots/status say `DATA UNAVAILABLE`; do not fabricate positions.

## Continuity and display

- On connection, send a bounded v1 snapshot first, with an explicit effective
  coverage box and source/availability state. The server assigns an opaque epoch
  and monotonic per-epoch sequence before writing to the client. Snapshot truncation
  and empty covered results are visible and are not interpreted as complete absence.
- Provider loss, overflow, stale source data, or an unknown licence invalidate
  continuity. Emit `stream.gap` with `replay_available=false`, then a replacement
  snapshot; disconnect clients unable to receive both. Do not replay old positions.
- Browser reducers clear positions on gaps and require a newer snapshot before
  accepting position updates. `LIVE` means current validated provider data only;
  show effective time, source attribution, and limitations beside any rendered
  observation. The status shell stays `OFFLINE` until the gateway is wired.
- No raw Pelyr frame, credential, full-frame log, persistent AIS record, free-form
  query, public vessel endpoint, or downloadable result is permitted in this slice.

## Review gate

B6.2 must propose exact route/session/origin behavior before registering a route
or activating worker startup. A reviews the threat boundary and frozen event
contract first; implementation then measures queue/load behavior before acceptance.
Backend tests verify rejection of missing and unapproved origins as well as
explicit production fail-closed behavior. This document does not authorize
deployment or claim usable live AIS in the current UI.
