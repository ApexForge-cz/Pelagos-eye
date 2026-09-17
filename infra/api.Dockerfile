FROM ghcr.io/astral-sh/uv:0.11.8 AS uv

FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd --system oceanscope && useradd --system --gid oceanscope oceanscope

WORKDIR /app
COPY --from=uv /uv /uvx /bin/
COPY apps/api/pyproject.toml apps/api/uv.lock ./
COPY apps/api/README.md ./README.md
COPY apps/api/src ./src
RUN uv sync --frozen --no-dev

COPY apps/api/alembic.ini ./alembic.ini
COPY apps/api/alembic ./alembic

RUN chown -R oceanscope:oceanscope /app
USER oceanscope

EXPOSE 8000
CMD ["uvicorn", "oceanscope_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
