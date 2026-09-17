# Direct Dependency Inventory

- Review date: 2026-09-17
- Sources of truth: `apps/api/uv.lock` and root `package-lock.json`
- Policy: direct dependencies require a current use; transitive dependencies remain locked
  and are reviewed by automated audit/update tooling.

## API runtime

| Package | Locked version | License | Reason |
| --- | ---: | --- | --- |
| Alembic | 1.20.0 | MIT | Versioned PostgreSQL/PostGIS migrations |
| FastAPI | 0.141.1 | MIT | Typed HTTP application and OpenAPI |
| GeoAlchemy2 | 0.20.0 | MIT | Typed PostGIS geography columns and spatial DDL integration |
| HTTPX | 0.28.1 | BSD-3-Clause | Bounded official-source HTTP downloads with proxy support |
| psycopg | 3.3.5 | LGPL-3.0-only | PostgreSQL driver for migrations/later repositories |
| pydantic-settings | 2.15.0 | MIT | Typed environment configuration and secret wrappers |
| SQLAlchemy | 2.0.54 | MIT | Repository and migration metadata foundation |
| structlog | 25.5.0 | MIT OR Apache-2.0 | Structured, correlation-friendly logs |
| Uvicorn | 0.53.0 | BSD-3-Clause | ASGI development/container server |

## API development

| Package | Locked version | License | Reason |
| --- | ---: | --- | --- |
| mypy | 1.20.2 | MIT | Strict static type checking |
| pytest | 8.4.2 | MIT | Python behavior tests |
| pytest-cov | 6.3.0 | MIT | Diagnostic coverage reports |
| Ruff | 0.16.8 | MIT | Python formatting and linting |

## Web runtime

| Package | Locked version | License | Reason |
| --- | ---: | --- | --- |
| React | 19.3.0 | MIT | Component runtime |
| React DOM | 19.3.0 | MIT | Browser rendering |

## Web development

The direct web development packages are Vite 8.3.0, TypeScript 6.0.3, Vitest 5.0.1,
ESLint 10.10.0, typescript-eslint 8.70.0, Prettier 3.9.7, jsdom 30.0.1, Testing Library,
React/Vite ESLint plugins, and type packages. All are MIT except TypeScript, which is
Apache-2.0. Exact versions and transitive packages are recorded in `package-lock.json`.

## Deferred dependencies

CesiumJS, MapLibre, deck.gl, ECharts, Tailwind, shadcn/ui, TanStack Query, Zustand, Polars,
GeoPandas, and other planned libraries are not installed merely because they appear in the
roadmap. They are added only when an authorized phase has a concrete consumer and tests.

## Notes

- The configured npm mirror does not implement the audit endpoint, so the documented local
  audit explicitly used `https://registry.npmjs.org` and found zero vulnerabilities.
- Package licenses do not grant rights to external maritime datasets.
- Container base images require a separate release-time image/SBOM and vulnerability review.
