# Multi-stage build for backend
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies in base stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies stage - install Python packages
FROM base AS dependencies

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# Copy project metadata and lockfile first to leverage Docker layer caching
COPY pyproject.toml uv.lock ./

# Install locked runtime dependencies from uv.lock
RUN uv sync --locked --no-dev --no-install-project --extra backend

# Production stage
FROM base AS production

# Copy virtual environment from dependencies stage (root-owned, read-only to appuser)
COPY --from=dependencies /opt/venv /opt/venv

# Copy backend source
COPY backend/src /app/backend/src

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/backend/src

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

WORKDIR /app/backend/src

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
