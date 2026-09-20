# Phase 4 Live AIS contract verification

**Status:** Contract proposal verified locally. Phase 4 remains `Planned`; no provider,
route, WebSocket, storage, vessel UI, or live-data claim is accepted by this record.

**Date:** 2026-09-19; cross-language fixture update verified 2026-09-20

## Verified surface

- The Python contract accepts only the proposed v1 snapshot, position, status, and gap event
  envelopes and forbids unknown fields.
- Position values use WGS 84 degrees, knots, and degree headings/courses with AIS unavailable
  sentinels excluded from valid ranges.
- All event, observation, ingestion, normalization, coverage, status, and gap times require
  explicit timezone information.
- `CACHED` requires a non-negative cache age; other source states reject cache age.
- `DATA UNAVAILABLE` and `NO COVERAGE` snapshots cannot carry vessel positions. An available,
  covered snapshot may be empty without being relabeled as unavailable or no coverage.
- v1 gap events cannot claim replay, and raw provider fields are rejected.
- Static AIS identity/voyage fields are absent because their independent observation time,
  provenance, merge, and conflict semantics have not been reviewed.
- The TypeScript mirror builds under strict project settings, and its shallow envelope check
  returns only a boolean rather than claiming full runtime payload validation.
- `test-fixtures/live-ais/v1-server-events.json` is the shared provider-neutral `TEST DATA`
  set for all four v1 discriminators. Python fully validates each payload through Pydantic;
  TypeScript consumes the same file and recognizes each frozen v1 envelope.

## Commands and results

| Check | Result |
| --- | --- |
| Backend Ruff format and lint across `apps/api` | Passed; 91 files formatted, no lint findings. |
| Backend strict mypy across `src` and `tests` | Passed; 83 source files checked. |
| Focused backend contract tests | Passed; 12 tests. |
| Backend non-ASGI suite with repository-local pytest temp directory | Passed; 94 tests, 1 PostGIS migration test skipped. |
| Frontend Prettier and ESLint | Passed. |
| Frontend Vitest | Passed; 9 tests in 3 files. |
| Frontend TypeScript and production Vite build | Passed. |
| `git diff --check` | Passed. |
| Manual changed-code credential pattern review | No credential values found. |

The non-ASGI backend run used:

```text
pytest --ignore=tests/test_health.py --ignore=tests/test_status_api.py \
  --basetemp=../../tmp/pytest-phase4-fixtures-20260920 --cov --cov-report=term-missing
```

## Remaining limitations and gates

- The current Windows sandbox hangs in the five existing `ASGITransport` health/status API
  tests. They were excluded from the completed local suite and remain required in Linux CI.
- The PostGIS migration test was skipped because no explicit disposable
  `OCEANSCOPE_TEST_DATABASE_URL` was configured. This proposal adds no migration.
- `gitleaks` is not installed locally; the configured GitHub Actions secret-scan job remains
  required before merge.
- The production build retains the existing warning for chunks above 500 kB. This contract
  adds no runtime import or bundle dependency.
- Issue #28 tracks the shared-fixture increment. Provider-rights issue #24 remains open and
  continues to block provider implementation.
- Current operating limits are recorded in `docs/33-aisstream-provider-verification.md`.
  Applicable rights, credentials, live schema mapping, demo scope, retention, queue budgets,
  reconnect behavior, and load/soak evidence remain Phase 4 implementation entry gates listed
  in `docs/31-phase-4-contract-kickoff.md`.
- No browser or screenshot check was needed because this change does not register or render a
  user-facing surface.
- The shared fixtures contain fixed, provider-neutral `TEST DATA` only. They neither reproduce
  provider records nor authorize a provider, route, storage, or production-data integration.
