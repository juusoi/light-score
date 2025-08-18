# Multi-stage build for frontend
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies in base stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Dependencies stage - install Python packages
FROM base AS dependencies

# Copy project metadata first to leverage Docker layer caching
COPY pyproject.toml ./

# Install runtime dependencies from pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .[frontend]

# Production stage
FROM base AS production

# Copy installed packages from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy frontend source
COPY frontend/src /app/frontend/src

ENV FLASK_APP=frontend.src.wsgi:app \
    BACKEND_URL=http://localhost:8000

EXPOSE 5000

WORKDIR /app/frontend/src

# Run as non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

CMD ["python", "-m", "gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "wsgi:application"]
