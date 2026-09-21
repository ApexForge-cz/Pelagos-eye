# Pelyr Live AIS provider verification

**Review date:** 2026-09-22

**Status:** Selected Phase 4 candidate; implementation remains gated on a self-service
credential and live connectivity/coverage evidence.

**Tracking issue:** [#37](https://github.com/ApexForge-cz/Pelagos-eye/issues/37)

## Decision

Use Pelyr OPEN-AIS as the preferred Phase 4 live-AIS provider candidate. It is a closer
replacement for AISStream than a single national feed because it provides a documented
AISStream migration endpoint, a stronger native streaming protocol, an HTTPS snapshot API,
and machine-readable per-source licence and attribution metadata.

This decision does not claim global coverage, production availability, or Phase 4
completion. Pelyr is a private, non-commercial pilot with no SLA and may change, suspend,
or discontinue access. Fintraffic and Norwegian open AIS remain direct-source fallbacks for
future separately reviewed adapters; AISStream issue #298 remains open as historical
follow-up but no longer blocks selection of a Phase 4 candidate.

## Official evidence

The following pages were retrieved and reviewed on 2026-09-22:

| Evidence | URL | Recorded version or role |
| --- | --- | --- |
| API terms | <https://pelyr.com/stream-terms> | Version 1.5, updated 2026-09-07 |
| Pelyr data licence | <https://pelyr.com/pelyr-data-license> | Version 1.1, dated 2026-09-07 |
| Stream overview | <https://dashboard.pelyr.com/en/docs/stream> | Native WebSocket endpoint and limits |
| Native protocol | <https://dashboard.pelyr.com/en/docs/stream/protocol> | `pelyr.v1` frames, gaps, sources, limits |
| AISStream migration | <https://dashboard.pelyr.com/en/docs/stream/aisstream> | Partial `/v0` compatibility and differences |
| HTTPS API | <https://dashboard.pelyr.com/en/docs/api> | snapshots, vessel detail, tracks, sources |

The project discovered Pelyr through a third-party comment on project issue #24, then
independently checked the official material above. The recommendation itself is not treated
as evidence.

## Access and protocols

- Native stream: `wss://stream.pelyr.com/v1/stream` with
  `Authorization: Bearer <key>`.
- AISStream migration endpoint: `wss://stream.pelyr.com/v0/stream`.
- HTTPS API: `https://api.pelyr.com`.
- Keys are created through the Pelyr portal after GitHub sign-in. This is self-service
  registration rather than an application for provider approval.
- The key must stay server-side and out of URLs, browser code, logs, fixtures, screenshots,
  and Git history.

OceanScope will target `/v1`, not `/v0`. Pelyr explicitly labels `/v0` as partial
compatibility that cannot be byte-for-byte verified against the former service. `/v1`
provides named WGS 84 bounds, confirmation frames, heartbeats, loss counters, explicit close
codes, nullable fields, and a source directory.

## Rights and restrictions

Pelyr responses can combine data governed by different licences. Every data frame or field
group carries a `license` id that must resolve against the current connection's
`welcome.sources[]` array or `GET /v1/sources` response. The source directory, licence id,
licence text, and attribution must be preserved as provenance; attribution strings must not
be hard-coded as if one source supplied every observation.

For data under Pelyr Data Licence 1.1:

- commercial use, analysis, in-product display, storage, and derived results are permitted;
- the required visible attribution is
  `AIS data from Pelyr (pelyr.com), Pelyr Data Licence 1.1`;
- raw data, files, feeds, position-report APIs, service relays, bulk downloads, and
  systematic extraction are prohibited;
- end users may see data inside the product, but they do not receive rights to the data;
- reasonable controls must prevent the product from becoming a data-extraction path; and
- use for navigation, collision avoidance, search and rescue, safety decisions, surveillance,
  harassment, or tracking individuals is prohibited.

Data attributed to Fintraffic, BarentsWatch, or Kystverket remains governed by its declared
CC BY 4.0 or NLOD licence. The provider terms say those open-data rights are not narrowed.
OceanScope must display every applicable attribution represented in a view or derived
result. An unknown licence id is a provenance failure: stop publishing the affected data and
reconnect or refresh the source directory.

The planned OceanScope client channel is therefore an internal, same-origin product
transport, not a public vessel-data API. It must use fixed bounds, response/connection
limits, an origin allowlist, no data export, no unrestricted query proxy, and no raw Pelyr
frames. A future public API, downloadable dataset, or unrestricted WebSocket requires a
separate source-by-source rights review and is not authorized here.

## Published operating limits

Default limits recorded from API Terms 1.5 include:

| Limit | Default |
| --- | --- |
| Active keys per account | 2 |
| Concurrent stream connections per account | 2 |
| Subscriptions per connection | 4 |
| Bounding boxes per subscription | 50 |
| Bounding boxes per connection | 80 |
| MMSI values per subscription | 500 |
| HTTPS vessel/track requests | 12 per minute per key and budget |
| `GET /v1/sources` | 1 per 60 seconds |

Runtime values from the `/v1` `welcome.limits` object are authoritative and must be checked
instead of assuming these defaults. Pelyr currently states that no output-byte or monthly
volume limit is enforced, but a value of `0` means unlimited, not zero, and this may change.

## Coverage and continuity limits

- Pelyr does not provide a global-coverage guarantee. Coverage depends on its current
  third-party feeds and community receivers.
- Source and licence membership may change between connections. The `welcome.sources[]`
  snapshot is fixed for one connection.
- The service has no SLA, completeness promise, accuracy guarantee, or durable stream replay.
- A heartbeat arrives every 20 seconds and reports loss information. Loss, throttling,
  reconnects, and unknown source ids must produce explicit OceanScope gap/status events.
- AIS identity, voyage, and position fields remain fallible observations. Provider
  plausibility flags are evidence inputs, not proof that a position is genuine or false.

The first slice uses a fixed Gulf of Finland box because Pelyr declares Fintraffic among its
open-data sources and Fintraffic has official Finnish-water coverage. Actual Pelyr access,
source ids, observations, latency, and coverage for that box still require a key-backed
smoke test. An empty stream does not prove coverage or vessel absence.

## Phase 4 entry gate

Before provider code begins, Developer A must:

1. create a Pelyr account/API key through the self-service portal without sharing the key;
2. place the key only in the approved local server environment variable path;
3. run a bounded smoke check that records no raw payload or credential;
4. verify the `/v1` welcome protocol, effective limits, source directory, attribution,
   heartbeat, and Gulf of Finland observations or explicit coverage notice; and
5. record whether the key has the `stream` capability.

After that evidence is accepted, Developer B may implement the adapter/normalizer in the
issue-scoped paths. Phase 4 remains `Planned` until the implementation issue is explicitly
opened and authorized. No credential, provider payload, or production record belongs in
this verification document.
