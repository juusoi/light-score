# Light Score – Copilot Instructions

## Architecture & Data Flow

- Three Python services: FastAPI API in `backend/`, Flask UI in `frontend/`, and ESPN parsing utilities in `functions/`.
- Weekly flow: `functions/src/main.py` fetches ESPN standings with `EspnClient`, writes `backend/src/data/standings_cache.json`; backend serves cached standings and live ESPN snapshots; frontend renders scoreboard + standings using backend APIs.
- Backend endpoints in `backend/src/main.py` call ESPN (`httpx`) and expose `/games/weekly`, `/games/weekly/context`, `/games/weekly/navigation`, `/standings`, `/standings/live`, `/teams`.
- Frontend `frontend/src/app.py` calls backend via `requests` (respect `BACKEND_URL`) and templates in `frontend/src/templates` for Teletext-style UI.

## Local Workflows

- Use uv-managed venv: `make dev-setup` creates `.venv` and syncs deps across all subprojects.
- Containers run via Podman by default: `make up` starts FastAPI (8000) + Flask (5000); set `DOCKER=docker` if needed.
- Tests fan out per package through `scripts/run-tests.sh` (invoked by `make test`) which runs pytest in `backend/src/utest`, `frontend/src/utest`, `functions/src/utest` with the root `.venv`.
- Linting/formatting uses Ruff (`make lint`, `make fmt`); types via `make ty` (ty check); `make ci` runs lint + ty + test; `make security` runs Bandit and pip-audit.

### E2E Testing (Playwright/TypeScript)

- E2E tests live in `e2e/tests/` using Playwright with TypeScript; run with `make test-e2e` (requires services up via `make up`).
- `make lint-e2e` runs ESLint, `make fmt-e2e` formats with Prettier, `make ty-e2e` runs TypeScript checks.
- `make ci-e2e` runs the full E2E CI pipeline (lint + ty + test).
- E2E tests use `bun` as the package manager; dependencies are installed automatically on first run.

## Backend Patterns (`backend/src/main.py`)

- `_get_weekly_games` caches ESPN scoreboard responses for `_GAMES_TTL_SECONDS` (60s); always propagate stale cache when ESPN fails instead of raising new errors.
- Game payloads must set Finnish timezone helpers: `start_time_finnish`, `start_date_time_finnish`, `game_time`; tests assert new fields even when `None` (`test_weekly_games_timezone_fields`).
- Navigation helpers (`get_season_navigation`, `/games/weekly/navigation`) enforce NFL week boundaries; keep transitions synced with tests in `backend/src/utest/test_navigation.py`.
- `/standings` serves the local cache file; `/standings/live` wraps `_get_live_standings` with a 5-minute TTL and defensive fallbacks. Reuse `_extract_minimal_standings` for normalized rows `{team,wins,losses,ties,division}`.
- When extending HTTP access, prefer `httpx` (already patched in tests). Mock `httpx.get` in unit tests to avoid live ESPN calls (`backend/src/utest/test_live_standings.py`).

## Frontend Patterns (`frontend/src/app.py`)

- Flask route `/` fetches backend data, splits games into history/live/upcoming, and renders Teletext HTML. Keep all new template data serializable and ready for Jinja loops.
- Respect network fallbacks: on `requests` errors, the page renders `home_no_api.html`; keep error handling broad enough to avoid crashing the UI.
- Navigation links come from backend `/games/weekly/navigation`; maintain param naming (`seasonType` camelCase) to match backend models and FastAPI query parsing.

## Functions / Data Ingestion (`functions/src`)

- `standings_parser.py` converts ESPN JSON into `ConferenceGroup` + `TeamStandingInfo` via `find_first` condition helpers; reuse these when parsing new stats to avoid duplicating key lookups.
- `save_standings_cache` writes the lightweight standings list consumed by backend tests; ensure parsers keep this minimal schema stable.
- Network access in functions uses async `httpx.AsyncClient`; async context manager handles cleanup—mirror this pattern for new API calls.

## Testing & Conventions

### Python Unit Tests

- Store new unit tests alongside code under the respective `utest/` package; prefer patching network calls and using fixture builders like `_scoreboard_payload()` from `backend/src/utest/test_main.py`.
- Tests assume Helsinki timezone formatting helper functions (`format_finnish_time`, `format_finnish_date_time`) remain resilient to malformed inputs; keep try/except guards when modifying them.
- Keep ESPN URLs configurable only where necessary; hard-coded constants live near the call sites so that tests can patch them.

### E2E Tests (Playwright)

- E2E tests in `e2e/tests/` follow the `<feature>.spec.ts` naming convention (e.g., `home.spec.ts`, `site-navigation.spec.ts`).
- API-specific tests live in `e2e/tests/api/` (e.g., `backend.spec.ts`, `integration.spec.ts`); shared utilities in `e2e/tests/utils/`.
- Use role-based locators (`getByRole`, `getByLabel`, `getByText`) for resilience and accessibility.
- Use auto-retrying web-first assertions (`await expect(locator).toHaveText()`); avoid hard-coded waits.
- Tests can run against different environments via `SERVICE_URL` (frontend) and `BACKEND_URL` env vars; local defaults to `localhost:5000` and `localhost:8000`.

## Deployment & Ops

- Dockerfiles per service build minimal images; `compose.yaml` orchestrates backend + frontend containers in dev.
- Terraform under `terraform/` provisions AWS Lightsail and remote state; follow docs in `docs/` for IAM and deployment sequencing.
