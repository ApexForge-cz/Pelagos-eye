# Phase 2 ingestion reproducibility manifest verification

- Verification date: 2026-09-18
- Scope: internal export of one stored ingestion run
- Command: `oceanscope-export-manifest --ingestion-run-id <uuid>`
- Schema: `oceanscope-ingestion-manifest-v1`

## Implemented contract

The operator CLI resolves an ingestion run through the provenance repository and emits a
stable JSON document. It includes source identity, official and terms URLs, attribution,
license and redistribution status, data/schema version, publication and retrieval times,
source URL, checksum algorithm and value, content-addressed artifact reference, import
parameters, code revision, run timestamps and counts, cache metadata, failure reason, and
all recorded quality issues.

The manifest is an internal reproducibility artifact. It is not exposed by the public API,
and its local artifact reference does not grant redistribution permission. WPI and
MarineCadastre records remain subject to their recorded source gates.

## Verification evidence

- service tests cover complete manifest export and an unknown run ID
- the CLI is registered as an installed project script
- Ruff format and lint checks: passed for 88 files
- strict mypy check: passed for 80 source files
- Linux backend suite: 84 passed, 1 skipped; the skipped destructive migration test passed
  separately against an explicitly named disposable PostGIS database
- production-container installation: passed
- real-run export: passed for Open-Meteo ingestion run
  `5ad94c77-6e79-4776-b974-3abf6ed65115`
- exported evidence included schema `oceanscope-ingestion-manifest-v1`, source and terms
  metadata, SHA-256 checksum and artifact reference, 24 accepted records, import parameters,
  and code revision `192a0c9`

## Remaining boundary

The command exports metadata for one existing run. It does not download missing artifacts,
rerun an import, package restricted data, or expose local storage through an HTTP route.
