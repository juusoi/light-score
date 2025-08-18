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

# Install runtime dependencies directly (avoid build-system during docker build)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir Flask>=3.0.0 Flask-Testing>=0.8.1 requests>=2.32.0 gunicorn>=22.0.0

# Copy frontend source
COPY frontend/src /app/frontend/src

ENV FLASK_APP=frontend.src.wsgi:app \
    BACKEND_URL=http://localhost:8000

EXPOSE 5000

WORKDIR /app/frontend/src

CMD ["python", "-m", "gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "wsgi:application"]
