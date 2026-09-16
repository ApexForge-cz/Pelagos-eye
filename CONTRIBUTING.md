# Contributing to OceanScope

OceanScope is currently a single-maintainer project. Focused issues and reproducible defect
reports are welcome; response times are not guaranteed.

## Prerequisites

- Git
- Python 3.13 and [uv](https://docs.astral.sh/uv/)
- Node.js 24 with npm
- Docker with Compose for the optional local infrastructure stack

Docker Desktop must be running before Compose builds or starts the containers on Windows.

## Bootstrap

```bash
uv sync --directory apps/api --python 3.13
npm ci
```

Copy `.env.example` to an ignored `.env` and enter local values when Compose or a later
provider integration needs them. Never commit that file or paste secrets into issues.

## Run

```bash
uv run --directory apps/api uvicorn oceanscope_api.main:app --reload
npm run web:dev
```

API health endpoints are `http://localhost:8000/health/live` and
`http://localhost:8000/health/ready`. The Vite development URL is printed by npm.

## Quality gate

Run the same checks used by CI:

```bash
python scripts/check.py
```

Individual commands are listed in `scripts/check.py`. Important behavior needs positive,
negative, boundary, and failure tests. Test data must remain under test-only paths and be
clearly labeled; production code may not import it.

## Change discipline

- Stay within the current authorized phase in `README.md`.
- Do not add a dependency without recording why it is needed.
- Keep FastAPI routes thin and place later business logic in services.
- Never fabricate production data or silently convert provider failure into fake values.
- Update the relevant ADR, source contract, risk, and public-status documentation.
- Include commands and evidence in pull requests, not only checked boxes.
