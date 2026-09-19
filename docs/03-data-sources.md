# Data Sources and Verification

Verified against official documentation and live official endpoints on **2026-09-17** for the
Phase 2 sources. URLs and terms can change; each integration must re-check the official
source before release. The separate AISStream review on 2026-09-19 records current
verification limits in `docs/33-aisstream-provider-verification.md`.

## Source matrix

| Source | Official access | Key | Format | Update/latency | Planned scope | Primary limitation | Fallback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AISStream | `wss://stream.aisstream.io/v0/stream` | Required | binary WebSocket frames containing UTF-8 JSON | event-driven | live AIS | no SLA or replay; coverage and activity vary | labeled last verified cache, then unavailable |
| MarineCadastre / AccessAIS | bulk downloads; AccessAIS ordering UI | No for public bulk access | compressed CSV; derived products vary | annual/archive publication, not live | U.S. historical AIS | U.S. waters; files are large; AccessAIS ordering can be unavailable | bulk archive mirror manifest; no global claim |
| UNECE UN/LOCODE | official release downloads | No | CSV, TXT, XML/MDB and linked-data formats depending release | official biannual release; pre-release continuous | location identifiers and functions | locations are not all ports; coordinates are coarse/optional | pin last official release |
| NGA WPI | official CSV and web viewer/downloads | No for download | CSV official; GeoPackage, JSON, shapefile, file geodatabase available | complete content updated monthly | port positions, characteristics, services | general reference only; not a substitute for charts | pin last verified CSV |
| Open-Meteo Marine | `https://marine-api.open-meteo.com/v1/marine` | No on free non-commercial tier; required for paid endpoint | JSON; CSV/XLSX options | model-dependent, typically 6–24 h updates | wave, swell, SST, current and sea-level context | numerical-model uncertainty; coastal limitations | bounded cache, alternate model if explicit, then unavailable |
| USGS Earthquakes | real-time GeoJSON feeds and FDSN event service | No | GeoJSON | summary feeds updated every minute | global earthquake context | preliminary events can be revised | last feed within TTL; query service for bounded history |

## 1. AISStream

### Official source

- Documentation: <https://aisstream.io/documentation>
- Service: <https://aisstream.io/>

### Technical contract evidence

- WebSocket endpoint: `wss://stream.aisstream.io/v0/stream`.
- The official example uses one complete subscription with `APIKey`, `BoundingBoxes`,
  and optional `FiltersShipMMSI` / `FilterMessageTypes` fields.
- The official example connects to `wss://stream.aisstream.io/v0/stream`; Python enables
  `deflate` compression and handles provider messages as UTF-8 JSON payloads.
- The official message-model repository defines the subscription envelope and common
  position/static-data message types.
- Historical planning notes recorded no SLA and no durable replay; these are not a
  current terms certification. See the pinned revisions and Cloudflare limitation in
  `docs/33-aisstream-provider-verification.md`.
- The backend must keep any API key server-side. Direct browser use and production
  proxying remain unauthorized until current terms are reviewed.

### Fields to retain

At minimum: message type, provider metadata, MMSI when present, ship name when present, latitude/longitude when present, message-specific payload, provider observation context, receive time, raw schema/message version, and ingestion identifiers. Position normalization includes speed over ground, course over ground, true heading, navigation status/validity where available. Fields vary by AIS message type and must not be assumed globally present.

### Engineering constraints

- Negotiate compression where supported and monitor whether it is enabled.
- Read continuously; apply backpressure and record any internal drop/coalescing.
- Reconnect using exponential backoff with jitter and resubmit the full subscription.
- Begin with bounded regions and message types; a whole-world promise requires measured bandwidth, storage, and source approval.
- Persist observations needed for replay because the provider will not replay missed events.

### License/use note

An API account and current provider terms are required. The official repositories
establish technical use, but the 2026-09-19 review could not retrieve the current
website terms and did not identify a reusable open-data license grant for redistributing
raw streams. Before implementation or public deployment, archive the applicable terms
and confirm display, caching, retention, commercial-use, and redistribution rights.
Treat this as a release blocker, not an assumed permission.

## 2. MarineCadastre / AccessAIS

### Official sources

- AccessAIS: <https://marinecadastre.gov/accessais/>
- NOAA AIS FAQ: <https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf>
- Example official metadata (2021): <https://www.fisheries.noaa.gov/inport/item/65082>
- Public bulk-data entry point referenced by AccessAIS: `https://marinecadastre.gov/ais`

### Verified scope

MarineCadastre is a BOEM, NOAA, and USCG partnership. It distributes historical Nationwide AIS observations for United States waters. It is suitable for the first reproducible history, track, and traffic-analysis feature, but it does **not** establish global historical coverage.

On the verification date, the AccessAIS page reported its ordering service unavailable while directing users to bulk downloads. The architecture must therefore treat bulk downloads and recorded manifests as the dependable ingestion path.

### Common archive fields

Official metadata lists fields including MMSI, `BaseDateTime` (UTC), latitude, longitude, speed over ground, course over ground, heading, vessel name, IMO identifier, call sign, vessel type, navigation status, length, width, draft, cargo, and transceiver class. Schemas differ by year; imports must select a versioned schema rather than assume all fields exist.

The current official daily bulk index republishes compressed `.csv.zst` files. A verified
2024 archive used lowercase snake-case headers such as `mmsi`, `base_date_time`,
`longitude`, `latitude`, and `transceiver`, while older documented downloads use names
such as `MMSI`, `BaseDateTime`, `LON`, `LAT`, and `TransceiverClass`. The importer maps
only these verified aliases and otherwise fails as a provider revision.

### Data quality and volume

- Validate year-specific metadata, geographic coverage, UTM zone/file partition, and checksum before import.
- Treat vessel-supplied static fields as observations that may be missing or wrong.
- Deduplicate exact/near duplicate messages with documented rules.
- Do not interpret absence as a vessel absence without accounting for receiver and archive coverage.
- Use columnar staging and bounded geographic/time subsets for development.

### License/use note

The official AIS FAQ permits derived public products and asks users to cite the data. It notes U.S. Government material is generally public domain in the United States while foreign copyrights may apply, and directs users to NAVCEN terms and dataset metadata. Preserve the requested citation and re-check metadata for each archive year.

### Fallback

Use a locally/object-stored copy only when redistribution and storage terms allow, with original URL, retrieval time, checksum, archive year/zone, and citation. If neither AccessAIS nor verified bulk archives are available, disable the affected date/area rather than substitute data.

### Implemented Phase 2 boundary

The internal importer constructs an official daily archive URL from an explicit UTC date
in the verified 2015–2025 schema range. Every run requires a non-antimeridian WGS 84 box
no larger than 5° by 5°, a UTC window no longer than six hours within that date, and a
record cap of at most 100,000. Download size and scanned-row limits are enforced. The
parser streams Zstandard data, validates identifiers, times and coordinates, treats AIS
sentinels as missing rather than zero, preserves fallible static fields as observations,
deduplicates exact records, and reports filtered, rejected, duplicate, and cap-truncated
counts separately. The raw archive remains internal with restricted redistribution state.
Direct official downloads are labeled `LIVE`; a checksummed local archive replay is
labeled `CACHED` with its age.
No global, live, ownership, or complete-coverage claim is made.

The status policy treats a newly retrieved archive as `LIVE` for one day and then as a
stored `CACHED` archive. Its cache window has no time expiry because the dated source
artifact is immutable and checksum-pinned; this does not imply that the upstream service
is currently reachable or that coverage is complete.

## 3. UNECE UN/LOCODE

### Official sources

- Publications: <https://unlocode.unece.org/publications/>
- Data attributes: <https://unlocode.unece.org/docs/data-attributes/>
- Directory/license notice: <https://unlocode.unece.org/directory/>
- Official release metadata: <https://opensource.unicc.org/api/v4/projects/64/releases/permalink/latest>

### Verified contract

- Official production releases are published twice yearly; a continuously updated pre-release also exists.
- Downloadable publication formats include CSV/TXT and other release artifacts; a SKOS vocabulary is available but marked under active development.
- Core fields include change indicator, country/location code parts, name, name without diacritics, subdivision, function, status, date, IATA field when different, coordinates, and remarks.
- Coordinates are encoded in degrees/minutes in the publication layout and are not precision port geometries.

### Interpretation rules

- `UN/LOCODE` identifies trade and transport locations. Use the function string to determine whether a record declares a port function; never label every row a seaport.
- The five-character identifier is country code plus three-character location code.
- Pin production release versions for reproducible behavior. Pre-release data, if ever exposed, must be labeled provisional.
- Preserve change indicators and status instead of deleting superseded entries without lineage.
- The importer resolves the official `UNLOCODE Data Archive` asset from release metadata,
  requires the documented 12-column publication rows, selects records whose fixed-width
  function string declares port function `1`, and stores the release tag plus SHA-256.

### License/use note

The official directory states UN/CEFACT standards are free to use under CC BY 4.0. Provide attribution, identify the release, and note modifications. Confirm that every bundled artifact carries compatible terms before redistribution.

### Fallback

Serve the last validated official release with its edition and `CACHED` state. Do not silently switch to pre-release content.

### Implemented Phase 2 query boundary

`GET /ports` exposes normalized UN/LOCODE rows from the latest usable ingestion run with
bounded pagination and optional name/code, country, and coordinate-availability filters.
Responses retain the release, source URL, attribution, timestamps, source state, and
quality flags. The query does not expose raw rows or infer canonical port identities.

## 4. NGA World Port Index

### Official sources

- WPI publication/download page: <https://msi.nga.mil/Publications/WPI>
- Official complete CSV: <https://msi.nga.mil/api/publications/world-port-index?output=csv>
- Official OpenAPI description: <https://msi.nga.mil/api/v3/api-docs>
- Feature service metadata: <https://vcps.nga.mil/nauticalpubs-feature/rest/services/WPI/World_Port_Index_Viewer/FeatureServer>

### Verified contract

- WPI is a worldwide port reference and planning aid with general locations and more than 100 characteristics/services.
- The official page identifies CSV as the official content format and also offers GeoPackage, JSON, shapefile, and file geodatabase downloads through the viewer.
- Complete content is updated monthly.
- The feature service uses spatial reference EPSG:4326 and documents a maximum record count of 3,000 for service queries; full imports should prefer the official CSV rather than fragile pagination against the viewer.
- The CSV endpoint did not provide a stable edition identifier, `ETag`, or
  `Last-Modified` value during verification. The importer therefore uses the file's
  SHA-256 as its immutable data version and the normalized header SHA-256 as its schema
  version; it does not invent a publication timestamp.

### Planned fields

The first importer retains the stable port number, name, country code, coordinates,
UN/LOCODE when present, every source column in the raw record, the content/schema hashes,
and quality flags. Broader typed mapping remains future work.

Retain the stable source key, port/country/region names, coordinates, UN/LOCODE when present, harbor/entrance attributes, size/type, maximum vessel dimensions where supplied, facilities, services, publication links, source edition, and raw values. The exact mapping must be generated from the current official “Explanation of Data Fields,” not inferred from an old edition.

### Limitations and license

NGA explicitly states WPI does not replace current charts and detailed publications. The 2019 publication states no copyright is claimed under U.S. law; current service metadata requests NGA attribution but has an empty machine-readable license field. Before redistributing a current snapshot, preserve attribution and complete a release-time terms review. Do not market WPI data as navigation-authoritative.

The current public port-query repository filters out WPI because its redistribution status
remains `unreviewed`. Internal ingestion and status metadata do not override that gate.

### Fallback

Pin the last verified official CSV with checksum and retrieval date. Use UN/LOCODE only for identifier/location fallback, not as a substitute for detailed WPI attributes.

## 5. Open-Meteo Marine API

### Official sources

- Marine documentation: <https://open-meteo.com/en/docs/marine-weather-api>
- Terms and limits: <https://open-meteo.com/en/terms>
- Pricing/commercial use: <https://open-meteo.com/en/pricing>

### Verified contract

- Endpoint: `https://marine-api.open-meteo.com/v1/marine`.
- Required coordinates are WGS 84 latitude/longitude; multiple coordinates are supported.
- Outputs include JSON and optional CSV/XLSX representations.
- Variables include wave height/direction/period, wind waves, swell components, sea-surface temperature, ocean-current velocity/direction, and sea-level height.
- Model resolution and update frequency differ. Examples documented at verification: global wave and ocean products range roughly from 5–50 km and update every 6–24 hours depending on model.
- Tides/currents and coastal values have explicit accuracy limitations and are not suitable for coastal navigation.

### Access and terms

The free endpoint requires no API key but is non-commercial, has no uptime guarantee, and is limited to 600 calls/minute, 5,000/hour, 10,000/day, and 300,000/month according to current terms. Commercial deployments require an appropriate paid plan/API key. Data is CC BY 4.0 with required attribution to Open-Meteo and underlying providers; attribution varies by selected model.

### Engineering constraints

- Cache by grid/coordinate, selected model, variables, units, and time window.
- Preserve model/source attribution, effective forecast time, retrieval time, units, resolution, and warnings.
- Do not call a modeled value an observation.
- Avoid dense per-pixel browser calls; obtain bounded grids/points through the backend and respect call accounting.

### Implemented Phase 2 boundary

The internal importer accepts one coordinate and 1–168 forecast hours per invocation. It
requests GMT, sea-cell selection, and the `best_match` routing mode for seven explicitly
supported variables. It stores requested and selected-grid coordinates separately,
preserves units and UTC valid times, retains a checksummed raw response, and rejects
misaligned, invalid, or entirely null rows without zero-fill. `best_match` is not treated
as proof of one underlying model. `GET /ocean/forecast` exposes the latest stored snapshot
matching an exact requested coordinate and a bounded time window of at most seven days. It
preserves requested/grid coordinates, units, valid times, provenance, and the coastal/model
warning. Scheduled refresh and cache fallback remain unimplemented.

### Fallback

Serve a cached forecast only within an explicit age threshold and retain its original valid time. If switching models, surface the model change; otherwise show unavailable.

## 6. USGS Earthquake GeoJSON

### Official sources

- Feed directory: <https://earthquake.usgs.gov/earthquakes/feed/>
- GeoJSON summary format: <https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php>
- Integrated past-hour feed: <https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson>
- FDSN event service: <https://earthquake.usgs.gov/fdsnws/event/1/>
- USGS copyright guidance: <https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted>

### Verified contract

- GeoJSON summary feeds cover past hour, day, seven days, and 30 days at several magnitude/significance thresholds.
- Summary feeds are updated every minute and are recommended for automated real-time display.
- A `FeatureCollection` includes generation metadata, bounding box, and point features.
- Relevant properties include magnitude, place, event time, updated time, detail URL, status, tsunami flag, significance and network/code fields; geometry coordinates are longitude, latitude, depth.
- Use the FDSN event API for bounded custom/history queries, not high-frequency recreation of standard feeds.
- The Phase 2 importer pins each feed generation and content checksum, validates point
  geometry/timestamps, and upserts only when the provider `updated` time advances.
- `GET /earthquakes` queries stored events only when both an offset-aware time window and
  a non-antimeridian WGS 84 bounding box are supplied. The time window is capped at 31
  days, pagination is bounded, and event, update, ingestion, and normalization times stay
  distinct in the response.

### Data semantics

- Earthquake solutions can be updated after first publication. Upsert by event ID and provider update time.
- Keep event time separate from record update time and ingestion time.
- A tsunami flag is provider metadata, not an OceanScope impact prediction.
- Depth is the third GeoJSON coordinate and must not be confused with elevation.

### License/use note

USGS-authored data and information are generally public domain in the United States; USGS asks for source acknowledgement and notes that some third-party content may differ. Credit USGS and link to event detail. Avoid any appearance of government endorsement.

### Fallback

Use the most recent successfully validated feed within a short documented TTL. Beyond it, mark delayed/offline. Store revisions for reproducibility where practical.

## Source onboarding checklist

No source enters production until all items pass:

- Official owner and documentation URL recorded
- Access method tested without exposing credentials
- Current terms/license archived or linked and redistribution reviewed
- Coverage, latency, update behavior, rate/cost limits documented
- Schema fixture and version/change detection added
- Range, enum, null, timestamp, coordinate, and identity validation defined
- Retry, timeout, circuit, caching, and fallback behavior defined
- Attribution text and UI placement defined
- Provenance mapping and raw-record retention decision documented
- Health and freshness thresholds approved
- Removal/rollback plan documented
