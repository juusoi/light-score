# Frontend Service

Flask-based web UI for NFL scores and standings with a Teletext-inspired design.

## Overview

The frontend fetches data from the backend API and renders it as HTML pages. Built with Flask and Jinja2 templates.

## Prerequisites

- Python 3.13+
- uv (<https://docs.astral.sh/uv/>)
- Backend service running on `:8000`

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
BACKEND_URL=http://localhost:8000 flask --app frontend/src/app.py run -p 5000
```

Or with containers (recommended):

```bash
make up  # Starts backend:8000 + frontend:5000
```

### Mock Mode

Run with mock ESPN data for testing playoffs and standings:

```bash
make mock-up
```

## Routes

| Route | Description |
|-------|-------------|
| `/` | Main scoreboard with games and standings |
| `/playoffs` | Playoff picture/bracket view |
| `/?seasonType=2` | Regular season view |
| `/?seasonType=3` | Postseason view |
| `/?week=N` | Specific week navigation |

## Templates

| Template | Purpose |
|----------|---------|
| `home.html` | Main scoreboard with games grid + standings |
| `home_no_api.html` | Fallback when backend is unavailable |
| `playoffs.html` | Playoff bracket visualization |

## Testing

```bash
cd frontend/src
../../.venv/bin/python -m pytest
```

Or from project root:

```bash
make test
```

## Key Files

| File | Purpose |
|------|---------|
| `src/app.py` | Flask app with routes and API integration |
| `src/wsgi.py` | WSGI entry point for production |
| `src/templates/` | Jinja2 HTML templates |
| `src/static/` | Static assets (CSS, images) |
| `src/utest/` | Unit tests |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://localhost:8000` | Backend API URL |

## Error Handling

When the backend is unavailable, the frontend gracefully degrades to `home_no_api.html` instead of crashing.
