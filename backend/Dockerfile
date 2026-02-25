# ── Base ────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base
WORKDIR /app

# System deps (curl for healthcheck, libpq for asyncpg)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# ── Dependencies ─────────────────────────────────────────────────────────────────
FROM base AS deps
COPY pyproject.toml .
# Install all deps (including dev) — keeps dev and prod images consistent in this project
RUN uv pip install --system -e ".[dev]"

# ── Development image (default) ───────────────────────────────────────────────────
FROM deps AS dev
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production image ──────────────────────────────────────────────────────────────
FROM deps AS prod
COPY src/ ./src/
COPY scripts/ ./scripts/
EXPOSE 8000
# No --reload in prod
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
