# Backend Service

FastAPI backend for NFL scores and standings.

## Overview

The backend fetches NFL data from ESPN APIs with caching and serves it via REST endpoints. Built with FastAPI and uses `httpx` for async HTTP requests.

## Prerequisites

- Python 3.13+
- uv (<https://docs.astral.sh/uv/>)

## Setup

From project root:

```bash
make dev-setup
# or manually:
uv venv
./scripts/uv-sync.sh --all
```

## Run Locally

```bash
cd backend/src
../../.venv/bin/uvicorn main:app --reload --port 8000
```

Or with containers:

```bash
make up  # Starts backend:8000 + frontend:5000
```

### Mock Mode

Run with fixture data instead of live ESPN:

```bash
MOCK_ESPN=true ../../.venv/bin/uvicorn main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Health check / API info |
| `/games/weekly` | Weekly games with scores |
| `/games/weekly/context` | Current week/season info |
| `/games/weekly/navigation` | Prev/next week links |
| `/standings` | Cached standings from local file |
| `/standings/live` | Live standings from ESPN (5-min TTL) |
| `/teams` | Team list with metadata |
| `/playoffs/bracket` | Playoff bracket with seeds and games |
| `/playoffs/picture` | Playoff race/status by conference |

Interactive docs available at `http://localhost:8000/docs`.

## Testing

```bash
cd backend/src
../../.venv/bin/python -m pytest
```

Or from project root:

```bash
make test
```

## Data Caching

- **Games**: 60-second TTL in memory
- **Live standings**: 5-minute TTL in memory
- **Cached standings**: Read from `data/standings_cache.json` (updated by `functions/`)

## Key Files

| File | Purpose |
|------|---------|
| `src/main.py` | FastAPI app with all endpoints |
| `src/data/standings_cache.json` | Cached standings data |
| `src/fixtures/` | Mock data for testing (playoffs, standings) |
| `src/utest/` | Unit tests |
