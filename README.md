# NFL Scores and Standings

Lightweight NFL scores and standings app with:

- FastAPI backend (example API)
- Flask frontend (renders backend data)
- Functions package (ESPN parser utilities, AWS Lambda-ready)

Everything is managed with a single project (pyproject-first) using uv for env/deps and a unified CI.

## Repo structure

- `backend/` — FastAPI app and tests
- `frontend/` — Flask app and tests
- `functions/` — ESPN integrations and parsers with tests
- `scripts/` — helper scripts for setup, tests, lint, formatting
- `pyproject.toml` — root metadata, extras, dev deps

## Prerequisites

- Python 3.13+
- uv (https://docs.astral.sh/uv/)

## Setup (pyproject-first)

```bash
# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# From project root
uv venv
./scripts/uv-sync.sh --all   # installs dev deps + all extras
```

````bash
uv venv
uv sync --extra backend --dev     # backend only
uv sync --extra frontend --dev    # frontend only
## Run locally

Backend (FastAPI):

 Frontend (Flask):
 - Uses BACKEND_URL=http://localhost:8000 (see `frontend/src/app.py`)
 - Start app on http://localhost:5000
 ```bash
 cd frontend/src
 ../../.venv/bin/python app.py
````

- Start API on http://localhost:8000

```bash
../../.venv/bin/uvicorn main:app --reload
```

Frontend (Flask):
Functions (ESPN parsers):

- Parse standings from ESPN and write `afc.json` and `nfc.json`. Also writes a backend cache file for quick e2e:
  `backend/src/data/standings_cache.json`

```bash
cd functions/src
../../.venv/bin/python main.py
```

- Uses BACKEND_URL=http://localhost:8000 (see `frontend/src/app.py`)
- Start app on http://localhost:5000

```bash
cd frontend/src
../../.venv/bin/python app.py
```

Functions (ESPN parsers):

- Parse standings from ESPN and write `afc.json` and `nfc.json`

## One-command local run

This starts both the backend (uvicorn) and frontend (Flask) and first generates the standings cache via the functions package. Useful for quick e2e checks.

```bash
./scripts/run-local.sh
```

```bash
cd functions/src
../../.venv/bin/python main.py
```

## Testing

Run all tests:

```bash
./scripts/run-tests.sh
```

Run per package:

```bash
cd backend/src   && ../../.venv/bin/python -m pytest -v
cd frontend/src  && ../../.venv/bin/python -m pytest -v
cd functions/src && ../../.venv/bin/python -m pytest -v
```

## Lint, format, type-check

```bash
./scripts/lint-and-format.sh
```

Tools:

- Ruff (lint + format)
- Ty (type check, non-blocking)

## CI

A single GitHub Actions workflow runs:

- Lint/format/type-check via uv environment
- Matrix tests for backend, frontend, and functions
- On PRs, each matrix job only runs if that folder has changes; on pushes, all run

See `.github/workflows/ci.yaml`.

## Notes and roadmap

- Functions currently parse standings via ESPN and save JSON to disk. AWS Lambda + DB integration is planned.
- Frontend expects backend at http://localhost:8000; update `BACKEND_URL` in `frontend/src/app.py` if needed.

## License

MIT — see [LICENSE](./LICENSE).
