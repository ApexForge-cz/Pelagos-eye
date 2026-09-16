# Security Plan

## Security objectives

Protect provider credentials, prevent unauthorized or abusive use, preserve data integrity and availability, minimize sensitive logging, and keep the public repository safe to clone and deploy.

## Assets

- AISStream and future provider API keys
- Database and Redis credentials
- Application signing/session secrets if accounts are added
- Provider data and permitted caches
- Provenance and analytical result integrity
- Deployment, GitHub, registry, and domain credentials
- Service availability and cloud budget

## Trust boundaries

1. Browser to OceanScope HTTP/WebSocket endpoints
2. OceanScope to external providers
3. API/workers to PostgreSQL/PostGIS and Redis
4. CI to package registries, containers, and deployment target
5. Public contributions to maintainer-controlled builds/releases

## Threats and controls

| Threat | Planned controls |
| --- | --- |
| API key exposed to browser/repository/log | server-only provider clients; secret manager/env injection; redaction; secret scanning; key rotation |
| Broad CORS or WebSocket origin abuse | explicit origin allowlist; validate `Origin`; authentication/authorization if private features exist |
| Unbounded spatial/time query DoS | required bounds, page/row limits, timeouts, cost-aware endpoints, rate limits |
| SQL injection | SQLAlchemy parameterization; no user-built SQL fragments; allowlisted sort/filter fields |
| GeoJSON/payload abuse | size/depth/feature limits, schema validation, geometry complexity limits, timeouts |
| Provider message poisoning | strict adapters, range checks, unknown field handling, quarantine, source separation |
| WebSocket resource exhaustion | connection quotas, heartbeat/idle timeout, bounded buffers, coalescing, slow-client disconnect |
| SSRF through source URLs | fixed provider base URLs, allowlists, no arbitrary URL fetch endpoint, network egress policy where available |
| XSS from vessel/port text | framework escaping, no raw HTML, sanitize rich content, CSP |
| Dependency/supply-chain compromise | lockfiles, update review, provenance/SBOM, dependency and container scanning, pinned actions |
| GitHub Actions secret exfiltration | minimal permissions, environment protection, no secrets for untrusted fork jobs, pinned action SHAs |
| Cache poisoning/stale confusion | versioned keys, validation before cache, explicit TTL/status, signed/authenticated internal access where relevant |
| Data tampering | checksums, immutable manifests/raw references, audit fields, least-privilege database roles |
| Prompt injection in later intelligence | treat source text as data, structured evidence, tool allowlists, output grounding, no secret access |
| Cost exhaustion | quotas, budgets/alerts, bounded subscriptions, circuit breakers, storage retention |

## Secrets policy

- Real values never appear in Git, screenshots, fixtures, errors, or documentation.
- `.env.example` contains names/comments only.
- Local `.env*` files are ignored; production uses platform secret injection.
- Fail fast when a required secret is absent; never insert a default credential.
- Rotate immediately after suspected exposure and purge/rewrite history only with an incident plan.

## Authentication and authorization

Public read-only browsing may not require accounts in v1. Any write capability—saved geofences, annotations, admin ingestion, provider configuration—requires authenticated authorization. Admin endpoints are separated, denied by default, audited, and not protected solely by obscurity.

## API and browser controls

- HTTPS/WSS only outside local development.
- Restrictive CORS; secure cookies and CSRF controls if cookie sessions are chosen.
- CSP, HSTS, `X-Content-Type-Options`, referrer and permissions policies configured for actual map/tile providers.
- Consistent validation and safe error bodies without stack traces or secrets.
- Upload/import endpoints, if added, enforce type, size, decompression-ratio, storage, and scanning limits.

## Database and infrastructure

- Separate application/migration/backup roles where operationally practical.
- Network-restrict databases and Redis; do not expose them publicly.
- Enable encrypted transport and encrypted backups on hosted environments.
- Parameterize queries and impose statement timeouts on analytical endpoints.
- Back up with retention and regularly test restoration.
- Container images run as non-root with minimal packages and read-only filesystem where practical.

## External provider handling

- Provider clients have explicit connect/read/total timeouts and bounded retry policies.
- Respect rate and connection limits; one user's viewport cannot rewrite global upstream subscriptions without control.
- Persist provider terms review date and owner.
- Do not proxy unrestricted raw provider feeds to unauthenticated clients.

## Logging and monitoring

- Structured logs use correlation IDs and source/run IDs.
- Redact authorization headers, query keys, cookies, connection strings, and sensitive payload fragments.
- Monitor authentication failures, rate-limit activity, provider disconnects, validation rejection spikes, unusual egress, storage growth, and cost thresholds.
- Retention is purpose-limited; do not log every raw AIS payload by default.

## Secure development lifecycle

1. Threat-model each new data source or externally reachable capability.
2. Review dependencies and permissions before addition.
3. Add misuse/failure tests with feature tests.
4. Run SAST, dependency, secret, and container scans in CI.
5. Review infrastructure and migrations before deployment.
6. Complete the release security checklist and archive evidence.

## Incident response outline

1. Detect and classify: secret, integrity, availability, abuse, dependency, or cost incident.
2. Contain: revoke key, disable source/route, block traffic, or freeze deployment.
3. Preserve relevant logs/manifests without expanding sensitive collection.
4. Eradicate and patch; add regression tests.
5. Restore from verified state and monitor.
6. Document impact, provider/user notification duties, and preventive actions.

## Security release gates

- Threat model current; no unreviewed trust boundary.
- No real secret in Git history or build artifacts.
- Critical/high findings resolved or release blocked.
- Rate/query/geometry/WebSocket bounds tested.
- Restore and key-rotation procedures exercised.
- External terms and attribution requirements satisfied.

