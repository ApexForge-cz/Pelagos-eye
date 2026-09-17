# Phase 2 data-status UI verification

- Verification date: 2026-09-17
- Scope: minimal local source/system status surface; no maritime record or map display
- API inputs: `GET /data/sources` and `GET /system/status`

## Implemented contract

The React client renders only values returned by the two read-only status APIs. It exposes
the controlled `LIVE`, `CACHED`, `DELAYED`, and `OFFLINE` source states; usable/unavailable
status; source and version links; UTC retrieval and completion times; ingestion status;
accepted/rejected counts; redistribution status; attribution; and quality-issue counts.

For a cached source, the displayed current age adds elapsed time since the recorded run to
the cache age captured by ingestion. Loading, empty-catalog, and request-failure states are
explicit. A failed request renders `DATA UNAVAILABLE`; it does not substitute zeros,
fixtures, or stale hard-coded values.

Vite proxies `/data` and `/system` to the local API during development. The production
Nginx image proxies the same paths to the Compose API service, so browser code remains
same-origin and contains no server credential or provider key.

## Verification evidence

- Prettier formatting check: passed
- ESLint with zero warnings: passed
- Vitest: 2 tests passed
- Strict TypeScript and Vite production build: passed
- Docker Compose API and web image builds: passed
- Nginx same-origin `/data/sources`: HTTP 200 with five real registered sources
- Nginx same-origin `/system/status`: HTTP 200 with API `READY` and database `LIVE`
- Real source-state response included four `LIVE` sources and the replayed NOAA archive as
  `CACHED`

Automated component tests cover the loading-to-ready path, a cached source with quality and
freshness evidence, and the unavailable path. The active automation environment did not
provide a browser, so screenshot/device visual inspection remains an explicit gate item.

## Remaining boundary

This status surface does not expose port, earthquake, forecast, or historical AIS records.
Bounded record-query APIs, explicit per-provider TTL/fallback policy, manual responsive
visual review, and map layers remain unfinished Phase 2 or later-phase work.
