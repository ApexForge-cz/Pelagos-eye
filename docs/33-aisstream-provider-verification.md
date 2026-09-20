# AISStream provider verification

**Review date:** 2026-09-19  
**Status:** Technical evidence recorded; provider implementation and public use remain blocked.

Tracking issue: [#24](https://github.com/ApexForge-cz/Pelagos-eye/issues/24).

## Decision

AISStream remains a candidate source for the Phase 4 live-AIS adapter, but it has not
passed the source-onboarding gate. The repository records enough official technical
evidence to map a future adapter, while display, caching, retention, storage,
redistribution, and commercial-use rights still require a current terms review.
No WebSocket connection, API key, worker, route, raw fixture, or production claim is
authorized by this record.

## Official technical evidence

The following repositories are maintained under the official AISStream organization and
were checked on 2026-09-19:

| Evidence | URL | Pinned revision | Relevant evidence |
| --- | --- | --- | --- |
| Service client repository | <https://github.com/aisstream/aisstream> | `3501dde210bc6d054659d312c646366cbdd4ada9` | README describes a free WebSocket global AIS API. |
| Official examples | <https://github.com/aisstream/example> | `19ad2acde7d7aca01fc45b0638051d752ec9a1f6` | Uses `wss://stream.aisstream.io/v0/stream`, `APIKey`, `BoundingBoxes`, `MessageType`, and `Message`; the Python example enables `deflate` compression. |
| Message models | <https://github.com/aisstream/ais-message-models> | `8650fc5bf8c308264bc0c18e9ddc83c3ec5d10b8` | OpenAPI definitions include `AisStreamMessage`, `SubscriptionMessage`, `PositionReport`, `ShipStaticData`, and other AIS message types. |

The service documentation and terms URLs are:

- <https://aisstream.io/documentation>
- <https://aisstream.io/terms>

Automated HTTP retrieval and browser inspection returned a Cloudflare `403` challenge
on the review date. Therefore the current website terms, limits, and any changes since
the repository evidence could not be independently archived in this review.

## Human browser follow-up - 2026-09-20

A user-assisted browser review reached the official
<https://aisstream.io/documentation#limits> page and confirmed the following displayed
operating limits:

| Constraint | Displayed limit | Operational meaning |
| --- | --- | --- |
| Subscribed connections per account | 3 | A fourth subscribed connection is rejected. |
| Open connections per originating IP | 3 | The limit applies before authentication. |
| Initial subscription | Within 3 seconds | The connection closes if no valid subscription arrives. |
| Subscription updates | 1 per second per connection | Faster updates close the connection; an update replaces rather than merges the prior subscription. |
| MMSI filter | 200 per subscription | Each MMSI must be a nine-character string. |
| Read behavior | Continuous | If a client cannot consume messages quickly enough and buffers fill, messages are discarded. |

The page also states that, starting September 2026, uncompressed connections are
limited by per-user bandwidth and messages beyond that limit are dropped. A future
adapter must negotiate compression, read continuously, bound internal queues, expose
gaps, and enforce the subscription/connection limits centrally.

The official <https://aisstream.io/terms> URL still did not expose readable terms in the
human browser. The rendered page and `view-source:` view both contained only one short
line of garbled text. This independently confirms that the current rights terms cannot
be reviewed from that endpoint; it does not imply permission.

## Historical rights evidence and its limit

In official issue [#25](https://github.com/aisstream/issues/issues/25), an AISStream
account replied in 2023 that there were no restrictions on use, while also providing no
SLA or uptime guarantee. This is historical support for the planning assumption that
technical experimentation may be possible; it is **not** treated as a current license,
redistribution grant, or authorization for a public or commercial deployment.

Open questions remain in official issues [#290](https://github.com/aisstream/issues/issues/290),
[#294](https://github.com/aisstream/issues/issues/294), [#295](https://github.com/aisstream/issues/issues/295),
and [#296](https://github.com/aisstream/issues/issues/296), which ask about data licensing,
storage, downstream JSON/GeoJSON reuse, public display, and commercial transformed
display. They did not provide a current, unambiguous grant that can close the source
gate.

## Current source-gate questions

Before implementation or release, the owner must archive the applicable current terms
and complete this source gate with a source URL and effective date:

1. Is public display of live and recently cached AIS observations allowed?
2. May OceanScope cache or persist raw messages, normalized positions, and track tails?
3. What retention period and deletion requirements apply?
4. Is redistribution, download, API exposure, or derived GeoJSON allowed?
5. Does commercial use or a public website require a paid plan or separate permission?
6. What connection, subscription, message, and rate limits are current, and how are
   they measured (account, IP, or deployment)? **Partially answered above.**
7. What attribution text, logo, or link is required?

Question 6 is now partially answered by the displayed limits above. R-02 remains an
active operational risk until those limits have enforcement and load evidence, but it is
no longer blocked on discovering the documented values. Until the rights questions are
answered and approved, R-03 and R-09 remain active Phase 4 entry blockers. The
provider-neutral contract in
`docs/31-phase-4-contract-kickoff.md` and `docs/32-phase-4-contract-verification.md`
is design evidence only.

## Safe next action

Request written clarification from the provider for questions 1-5 and 7, including the
applicable terms URL or effective date. Do **not** send or record an API key or token.
