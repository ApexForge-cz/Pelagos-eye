# B2 provider contract regression verification

**Issue:** [#34](https://github.com/ApexForge-cz/Pelagos-eye/issues/34)

**Date:** 2026-09-21

**Branch:** `test/provider-contract-regression`

**Owner:** Developer B

## Outcome

Seven focused regression tests now protect the existing port, USGS earthquake,
Open-Meteo marine forecast, and MarineCadastre historical AIS provider/parser
boundaries. The tests use only inline, minimized `TEST DATA` and mocked HTTP
transports. They do not call a real provider or load test data through production
configuration.

The new tests passed against the existing production code. No production defect was
found, so no parser, provider, public contract, migration, frontend, dependency, or
configuration change was made.

## Regression coverage

| Module | Test behavior | Risk controlled |
| --- | --- | --- |
| UN/LOCODE provider | Rejects a release asset URL outside the official host | Prevents an untrusted artifact from being accepted as an official release |
| WPI parser | Rejects a CSV missing the required longitude column | Prevents provider schema drift from producing incomplete port records |
| USGS parser | Accepts an empty `FeatureCollection` as a valid empty result | Keeps empty results distinct from provider unavailability |
| USGS parser | Rejects an event with an invalid event timestamp | Prevents malformed temporal data from reaching normalized records |
| Open-Meteo parser | Preserves a partially null row with null values and a coverage warning | Prevents missing values from becoming zero while retaining usable model data |
| Open-Meteo provider | Converts an upstream HTTP failure to `MarineDownloadError` | Keeps provider unavailability distinct from an empty forecast |
| MarineCadastre parser | Rejects an invalid MMSI and nulls invalid optional values with quality flags | Prevents invalid identity and numeric observations from becoming valid production values |

The focused suite increased from 31 to 38 passing tests. Combined statement/branch
coverage for the eight directly exercised provider/parser modules increased from 80%
to 82%; coverage was used to find meaningful failure branches, not as an acceptance
target.

## Files changed

- `apps/api/tests/test_port_parsers.py`
- `apps/api/tests/test_port_providers.py`
- `apps/api/tests/test_earthquake_feed.py`
- `apps/api/tests/test_marine_forecast.py`
- `apps/api/tests/test_historical_ais.py`
- `docs/b-deliveries/B2-provider-contract-regression.md`

No standalone fixture file was necessary. Existing test-only builders produce the
smallest relevant payloads and label their sources, versions, names, or artifacts as
`TEST DATA`.

## Verification

The repository's `uv` executable was not available on `PATH`, so the equivalent
executables from the existing `apps/api/.venv` environment were used.

```text
apps/api/.venv/Scripts/python.exe -m pytest \
  apps/api/tests/test_port_parsers.py \
  apps/api/tests/test_port_providers.py \
  apps/api/tests/test_earthquake_feed.py \
  apps/api/tests/test_marine_forecast.py \
  apps/api/tests/test_historical_ais.py -q
Result: 38 passed

apps/api/.venv/Scripts/ruff.exe format --check .
Result: passed; 94 files already formatted

apps/api/.venv/Scripts/ruff.exe check .
Result: passed

apps/api/.venv/Scripts/mypy.exe src tests
Result: passed; 86 source files checked

apps/api/.venv/Scripts/python.exe -m pytest --cov --cov-report=term-missing
Result: 114 passed, 1 skipped; total coverage 75%
```

`git diff --check` and the configured targeted secret scan are part of the final
delivery check and must pass before handoff.

## Remaining limitations

- `test_provenance_migration.py` was skipped because
  `OCEANSCOPE_TEST_DATABASE_URL` did not name an explicit disposable test database.
- Pytest reported that it could not update its cache under
  `apps/api/.pytest_cache`; this did not affect test execution or results.
- These tests intentionally use mocked provider responses. They verify contract and
  failure semantics, not current external-service availability.
- Uncovered branches remain in the existing providers and parsers. No additional
  tests are proposed here solely to increase a coverage percentage.

No follow-up issue is required from this increment. A future provider schema change or
an integration failure should receive its own scoped issue.

## Rollback

Revert this test-and-documentation change. No production code, schema, stored data, or
runtime configuration requires rollback.
