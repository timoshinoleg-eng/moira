# syntax=docker/dockerfile:1
# Moira bot — production image (python:3.11-slim, non-root, uv).

FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:${PATH}"

# uv (single static binary, official installer script).
FROM base AS build
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Final runtime image.
FROM base
RUN useradd --system --create-home --shell /usr/sbin/nologin moira
COPY --from=build /root/.local /root/.local
COPY --chown=moira:moira --from=build /app/.venv /app/.venv

WORKDIR /app
COPY bot bot/
COPY alembic alembic/
COPY alembic.ini ./
COPY .env.example .env.example
COPY assets assets/

USER moira

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["/app/.venv/bin/python", "-m", "bot._healthcheck"]

ENTRYPOINT ["/app/.venv/bin/python", "-m", "bot.main"]