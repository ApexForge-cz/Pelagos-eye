# Phase 2 data-status UI verification

- Verification date: 2026-09-18
- Scope: minimal local source/system status surface; no maritime record or map display
- API inputs: `GET /data/sources` and `GET /system/status`

## Implemented contract

The React client renders only values returned by the two read-only status APIs. It exposes
the controlled `LIVE`, `CACHED`, `DELAYED`, and `OFFLINE` source states; usable/unavailable
status; source and version links; UTC retrieval and completion times; ingestion status;
accepted/rejected counts; redistribution status; attribution; and quality-issue counts.

The API computes data age and effective cache age at request time from the approved source
policy. The client displays that age beside the effective state. Loading, empty-catalog,
and request-failure states are explicit. A failed request renders `DATA UNAVAILABLE`; it
does not substitute zeros, fixtures, or stale hard-coded values.

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
- Final real source-state response included three `LIVE` sources, the replayed NOAA archive
  as `CACHED`, and the expired USGS snapshot as `OFFLINE` / `DATA UNAVAILABLE`
- Web-container HTTP smoke check returned 200 for the application shell, hashed JavaScript
  asset, `/data/sources`, and `/system/status`; the proxied system state was `READY`

Automated component tests cover the loading-to-ready path, a cached source with quality and
freshness evidence, and the unavailable path. The active automation environment exposed no
browser surface, so screenshot/device visual inspection could not be performed and is
recorded as a non-blocking local verification limitation.

## Remaining boundary

This status surface does not itself expose port, earthquake, forecast, or historical AIS
records. Separate bounded UN/LOCODE `GET /ports`, USGS `GET /earthquakes`, and Open-Meteo
`GET /ocean/forecast` queries are implemented. Restricted historical AIS remains internal.
Manual responsive visual review remains a follow-up before claiming broad device support.
Map layers belong to Phase 3 and remain unimplemented.
