# B5 offline Pelyr position normalizer

**Issue:** [#41](https://github.com/ApexForge-cz/Pelagos-eye/issues/41)

**Branch:** `ais/offline-position-normalizer`

**Owner:** Developer B

## Scope

This delivery adds a network-free adapter for one Pelyr `/v1` `position` frame. It
normalizes a provider frame into the existing provider-neutral `LiveAisPosition` contract.
It does not connect to Pelyr, read credentials, open a WebSocket, persist data, expose a
route, or implement a worker, gateway, cache, or UI.

## Mapping

| Pelyr input | Normalized output | Rule |
| --- | --- | --- |
| envelope `type` | adapter dispatch guard | Must be exactly `position` |
| `id` | `provenance.source_event_id` | Used only as provider event provenance |
| `license` | source directory lookup | Must resolve in the connection's source directory |
| source `license` / `attribution` | `provenance.data_version` / `attribution_text` | Source id and licence are preserved in the version string; attribution is copied exactly |
| `data.mmsi` | `mmsi` | Integer or text normalized to exactly nine decimal digits |
| `data.msg_type` | `provenance.provider_message_type` | Required integer or text provider message type |
| `data.lat` / `data.lon` | `latitude` / `longitude` | Finite WGS 84 degrees within bounds |
| `data.sog` | `speed_over_ground_knots` | Nullable; finite and `0 <= value < 102.3` |
| `data.cog` | `course_over_ground_deg` | Nullable; finite and `0 <= value < 360` |
| `data.heading` | `true_heading_deg` | Nullable integer and `0 <= value < 360` |
| `data.rx_ts` | `observed_at` | Required timezone-aware ISO-8601 timestamp normalized to UTC |
| explicit `ingested_at` / `normalized_at` | provenance processing times | Required timezone-aware inputs normalized to UTC |

`observation_id` is deterministically formed from the resolved source id and provider frame
`id`. The source prefix prevents frame-id collisions between providers, while the frame id
prevents different reports received for one vessel in the same second from colliding. The
provider frame `id` is not treated as vessel identity or a cross-source ordering key.

The frozen public v1 contract has no provider-specific licence columns. The adapter keeps
the resolved source id and licence identifier in `provenance.data_version` using the
`pelyr-v1/source-<id>/<licence>` format, while preserving the exact runtime attribution in
`attribution_text`.

## Licence gate

The source directory is connection-scoped and must be supplied by the caller. Unknown source
ids, source `0`, `NOASSERTION`, and empty attribution are rejected before a position can be
published. The reviewed fictional test directory covers Pelyr, Fintraffic, Kystverket, and
BarentsWatch attribution selection. Provider-specific source metadata is never replaced by a
hard-coded Pelyr attribution.

Unknown provider fields are ignored at the adapter boundary and cannot appear in the
normalized Pydantic model. No missing numeric field is converted to zero.

## Verification

The focused tests cover valid normalization, UTC conversion, nullable AIS values, malformed
and out-of-range values, missing required fields, unknown fields, unknown source ids,
unpublishable licence metadata, and all reviewed attribution variants.

The implementation remains offline; no provider availability or live coverage claim is made
by this delivery. Local verification completed with:

```text
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q
Result: 142 passed, 1 skipped

apps/api/.venv/Scripts/ruff.exe format --check apps/api
Result: 97 files already formatted

apps/api/.venv/Scripts/ruff.exe check apps/api
Result: all checks passed

apps/api/.venv/Scripts/mypy.exe apps/api/src apps/api/tests
Result: success; no issues found in 89 source files

git diff --check
Result: passed
```

The one skipped test requires `OCEANSCOPE_TEST_DATABASE_URL` to name an explicit disposable
database. Pytest also reports a local cache-write warning because the sandbox does not permit
writes to `apps/api/.pytest_cache`; neither limitation changed test execution.

## Rollback and limitations

Rollback is a revert of the adapter, its focused tests, and this delivery note. No production
data, migration, runtime configuration, external dependency, or persistent storage is changed.
The adapter intentionally does not handle Pelyr transport frames, reconnects, source refresh,
continuity events, or public delivery; those belong to later authorized work.
