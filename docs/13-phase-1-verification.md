# Phase 1 Verification Record

- Date: 2026-09-17
- Scope: Engineering foundation only
- Status: In progress pending remote CI and container build

## Implemented

- Git repository connected to `ApexForge-cz/Pelagos-eye` with `main` as the baseline.
- Python 3.13 API package managed by uv with a committed lockfile.
- React/TypeScript/Vite web shell managed by npm workspaces with a committed lockfile.
- Typed server settings, secret-safe fields, structured request logs, correlation IDs,
  RFC-style validation errors, liveness, and readiness endpoints.
- Alembic configuration and an empty baseline migration; no business tables exist.
- Dockerfiles and a local Compose topology for web, API, PostGIS, and Redis.
- Ruff, mypy, pytest/coverage, ESLint, Prettier, Vitest, TypeScript build, and pinned CI.
- GitHub issue/PR templates, contribution guidance, conduct policy, and secret-scan job.

## Local evidence

`python scripts/check.py` passed on Windows with Python 3.13.7 and Node.js 24.21.0:

- Ruff format: passed
- Ruff lint: passed
- mypy strict: passed for 13 source/test files
- pytest: 4 passed
- Python coverage: 85%
- Prettier check: passed
- ESLint: passed with zero warnings
- Vitest: 1 test passed
- TypeScript/Vite production build: passed

Additional checks:

- `docker compose config --quiet`: passed with ephemeral local validation variables
- `alembic upgrade head --sql`: generated a valid empty baseline migration
- `npm audit --registry=https://registry.npmjs.org --audit-level=high`: 0 vulnerabilities
- `git diff --check`: passed after whitespace cleanup
- Forbidden aviation terminology and fake-data patterns: no matches in maintained source/docs

## Pending evidence

- Docker image build could not run because Docker Desktop's Linux engine was not running.
- The first GitHub Actions run passed backend, frontend, and Gitleaks jobs. A maintenance
  follow-up upgraded actions that GitHub reported as using deprecated Node.js 20 runtimes;
  the follow-up run is the final remote gate.
- No PostGIS/Redis integration test exists yet because Phase 1 has no domain persistence.

Phase 1 must remain **In progress** until container build and remote CI are green. This does
not block local API/web development, but it blocks claiming the phase gate is complete.
