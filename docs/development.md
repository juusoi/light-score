# Development

## Setup

```
uv venv
./scripts/uv-sync.sh --all
source .venv/bin/activate
```

## Run

Backend:

```
uvicorn backend.src.main:app --reload --port 8000
```

Frontend:

```
BACKEND_URL=http://localhost:8000 flask --app frontend/src/app.py run -p 5000
```

## Tests

```
./scripts/run-tests.sh
```

## Lint & Security

```
./scripts/lint-and-format.sh
make security || true
```

## Placeholders

Docs use ALL_CAPS placeholders (ACCOUNT_ID, TF_STATE_BUCKET, etc.).
