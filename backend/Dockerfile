FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl && \
    rm -rf /var/lib/apt/lists/*

# Copy project metadata first to leverage Docker layer caching
COPY pyproject.toml ./

# Install runtime dependencies directly
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi>=0.115.0 uvicorn>=0.30.0 pydantic>=2.9.0 httpx>=0.27.0 requests>=2.32.0

# Copy backend source
COPY backend/src /app/backend/src

ENV PYTHONPATH=/app/backend/src

EXPOSE 8000

WORKDIR /app/backend/src

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
