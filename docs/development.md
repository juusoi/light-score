# Development

## Setup

```
just dev-setup
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
just mock-up
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
just test
```

### E2E Tests

Requires services running (`just up` or `just mock-up`):

```bash
cd e2e
SERVICE_URL=http://localhost:5000 npx playwright test
```

Or use just recipe:

```bash
just test-e2e
```

## Lint & Security

```
just lint fmt ty
just security
```

## API Endpoints

| Endpoint | Description |
| -------- | ----------- |
| `/games/weekly` | Weekly games with scores |
| `/games/weekly/context` | Current week/season info |
| `/games/weekly/navigation` | Prev/next week links |
| `/standings` | Cached standings from local file |
| `/standings/live` | Live standings by division |
| `/teams` | Team list with metadata |
| `/playoffs/bracket` | Playoff bracket with seeds and games |

## Placeholders

Docs use ALL_CAPS placeholders (ACCOUNT_ID, TF_STATE_BUCKET, etc.).
