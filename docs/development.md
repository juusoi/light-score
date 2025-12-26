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

### Mock Mode

Run with mock ESPN data for testing without live API:

```bash
MOCK_ESPN=true uvicorn backend.src.main:app --reload --port 8000
```

Or with containers:

```bash
make mock-up
```

Mock fixtures are in `backend/src/fixtures/`:
- `regular_season.json` - Week 15 regular season games
- `postseason_wildcard.json` - Wild Card round
- `postseason_divisional.json` - Divisional round
- `postseason_conference.json` - Conference championships
- `postseason_superbowl.json` - Super Bowl
- `standings.json` - Full 32-team standings
- `playoff_seeds.json` - AFC/NFC seeds with game results

## Tests

```
./scripts/run-tests.sh
```

### E2E Tests

Requires services running (`make up` or `make mock-up`):

```bash
cd e2e
SERVICE_URL=http://localhost:5000 npx playwright test
```

Or use Make target:

```bash
make test-e2e
```

## Lint & Security

```
./scripts/lint-and-format.sh
make security || true
```

## API Endpoints

| Endpoint | Description |
| -------- | ----------- |
| `/games/weekly` | Weekly games with scores |
| `/games/weekly/context` | Current week/season info |
| `/standings/live` | Live standings by division |
| `/playoffs/bracket` | Playoff bracket with seeds and games |
| `/playoffs/picture` | Playoff race/status by conference |

## Placeholders

Docs use ALL_CAPS placeholders (ACCOUNT_ID, TF_STATE_BUCKET, etc.).
