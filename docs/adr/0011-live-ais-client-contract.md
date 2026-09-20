# ADR-0011: Live AIS client contract and continuity semantics

- Status: Proposed
- Date: 2026-09-19
- Owners: Developer A (public contract), Developer B (provider and delivery review)

## Context

Phase 4 needs a provider-neutral boundary before the AIS provider, worker, storage, gateway,
and frontend can be implemented independently. A bare vessel-position payload would hide the
important failure modes: provider disconnections, gateway backpressure, client loss, stale
cache, and geographic non-coverage. It could also leak provider dictionaries into the public
API and make missing data look like an empty sea.

This proposal freezes only the client-facing v1 vocabulary. It does not authorize an
AISStream integration, retention policy, database migration, public route, or live-data claim.

## Decision

- Version every server event with `protocol_version = "1.0"` and reject unknown versions.
- Use four discriminated server events: `vessel.snapshot`, `vessel.position`,
  `stream.status`, and `stream.gap`.
- Give every event a `stream_epoch` and monotonic `sequence`. A changed epoch or skipped
  sequence requires a new snapshot; sequence values are not durable replay offsets.
- State explicitly that v1 has no replay. Every detected provider, server, client, or
  subscription continuity gap emits `stream.gap` with `replay_available = false`.
- Keep connection state separate from source state, availability, and coverage. `CONNECTED`
  is transport state; it is not proof that a region has observations.
- Preserve observation, ingestion, normalization, and emission times. Normalize provider
  sentinel values to `null` and retain quality flags instead of inferring defaults.
- Keep static AIS identity out of the position contract until an independent identity
  observation time and provenance shape is reviewed; position provenance cannot be reused.
- Send only normalized, client-safe observations. Raw provider messages and API keys never
  cross the public contract.
- Require explicit WGS 84 bounds for `COVERED`; v1 bounds do not cross the antimeridian.
  `NO COVERAGE`, `DATA UNAVAILABLE`, and an available empty result remain distinct states.

The executable proposal lives in
`apps/api/src/oceanscope_api/api/contracts/live_ais.py`; the frontend mirror lives in
`apps/web/src/api/liveAis.ts`.

## Consequences

- Frontend work can design honest reconnect, gap, cache, and no-coverage states without a
  production provider or fabricated vessel records.
- The gateway must produce snapshots after connection/epoch changes and account for any
  coalesced or dropped updates.
- The provider implementation must map its source schema into this contract and preserve
  provenance rather than exposing raw envelopes.
- Vessel name, IMO, call sign, ship type, dimensions, and destination require a separately
  reviewed static/voyage observation contract before they can appear in search or detail UI.
- A later replay service would require a protocol revision or a separate historical API.
- The duplicated Python and TypeScript shapes share one authoritative provider-neutral fixture
  set. Contract changes and any future real route must update and pass both consumers.

## Alternatives considered

- Expose provider envelopes directly: rejected because it couples clients to an unstable
  external schema and can leak fields that have not passed redistribution review.
- Send positions only and infer health from silence: rejected because silence cannot
  distinguish empty traffic, no coverage, disconnection, or backpressure.
- Promise reconnect replay from in-memory buffers: rejected because the planned upstream has
  no durable replay guarantee and retention is not yet approved.
