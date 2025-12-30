# Repository Guidelines

## Architecture & Data Flow

- Three Python services: FastAPI API in `backend/`, Flask UI in `frontend/`, and ESPN parsing utilities in `functions/`.
- Weekly flow: `functions/src/main.py` fetches ESPN standings with `EspnClient`, writes `backend/src/data/standings_cache.json`; backend serves cached standings and live ESPN snapshots; frontend renders scoreboard + standings using backend APIs.
- Backend endpoints in `backend/src/main.py` call ESPN (`httpx`) and expose `/games/weekly`, `/games/weekly/context`, `/games/weekly/navigation`, `/standings`, `/standings/live`, `/teams`, `/playoffs/bracket`, and `/playoffs/picture`.
- Frontend `frontend/src/app.py` calls backend via `requests` (respect `BACKEND_URL`) and templates in `frontend/src/templates` for Teletext-style UI.

## Project Structure & Module Organization

- `backend/src` hosts the FastAPI service (`main.py` entrypoint); add domain modules under descriptive subpackages and keep JSON caches in `data/`.
- `frontend/src` contains the Flask UI with `templates/` and `static/`; route helpers live beside the app factory.
- `functions/src` holds ESPN parsing jobs; trigger ad-hoc refreshes with `python functions/src/main.py`.
- Co-locate Python unit tests under each `src/utest/` package; store E2E Playwright tests in `e2e/tests/`. Reference operational notes in `docs/`, automation in `scripts/`, and infrastructure in `terraform/`.

## Build, Test, and Development Commands

- Use uv-managed venv: `make dev-setup` creates `.venv` and syncs deps across all subprojects.
- Containers run via Podman by default: `make up` starts FastAPI (`:8000`) + Flask (`:5000`); set `DOCKER=docker` if needed.
- **Mock mode**: `make mock-up` starts services with `MOCK_ESPN=true` for testing with fixture data (playoffs, standings) without live ESPN calls.
- `make build-images` rebuilds when dependencies shift; `make down` stops containers.
- Tests fan out per package through `scripts/run-tests.sh` (invoked by `make test`) which runs pytest in `backend/src/utest`, `frontend/src/utest`, `functions/src/utest` with the root `.venv`.
- `make ci` runs lint + types + tests in one pass.
- Linting/formatting uses Ruff (`make lint`, `make fmt`); types via `make ty` (ty check); `make security` runs Bandit and pip-audit; `make health` performs a quick API smoke.

### E2E Testing Commands (Playwright/TypeScript)

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

## Coding Style & Naming Conventions

- Python 3.13+ with uv-managed virtualenv; use absolute imports and module-level constants for shared configuration.
- Follow Ruff defaults: four-space indentation, 99-character lines, snake_case modules, and descriptive function names.
- Name FastAPI paths with nouns (`/scores`, `/standings`) and align Flask templates with their routes (`templates/scores.html`).
- Run `make fmt` before committing to keep formatting clean.
- E2E tests use TypeScript with Playwright; follow `<feature>.spec.ts` naming convention.

## Testing Guidelines

### Python Unit Tests

- Write pytest tests named `test_*` inside the closest `src/utest/`; isolate fixtures under `utest/fixtures/`.
- Store new unit tests alongside code under the respective `utest/` package; prefer patching network calls and using fixture builders like `_scoreboard_payload()` from `backend/src/utest/test_main.py`.
- Mock external HTTP calls with `httpx` mock transports or local sample payloads—no live ESPN traffic in CI.
- Tests assume Helsinki timezone formatting helper functions (`format_finnish_time`, `format_finnish_date_time`) remain resilient to malformed inputs; keep try/except guards when modifying them.
- Keep ESPN URLs configurable only where necessary; hard-coded constants live near the call sites so that tests can patch them.
- Keep tests deterministic and fast; ensure `make test` and `make ci` pass locally before pushing.

### E2E Tests (Playwright)

- Store E2E tests in `e2e/tests/` with `.spec.ts` extension; group by feature (e.g., `home.spec.ts`, `site-navigation.spec.ts`).
- API-specific tests live in `e2e/tests/api/` (e.g., `backend.spec.ts`, `integration.spec.ts`); shared utilities in `e2e/tests/utils/`.
- Use role-based locators (`getByRole`, `getByLabel`, `getByText`) for resilience and accessibility.
- Use auto-retrying web-first assertions (`await expect(locator).toHaveText()`); avoid hard-coded waits.
- Tests can run against different environments via `SERVICE_URL` (frontend) and `BACKEND_URL` env vars; local defaults to `localhost:5000` and `localhost:8000`.
- Run `make test-e2e` with services up (`make up`) before pushing UI changes.

## Commit & Pull Request Guidelines

- Use Conventional Commits (e.g., `feat: add standings endpoint`) with ≤72-character summaries and focused scope.
- Link issues, document manual checks, and attach screenshots or curl snippets when UI or API responses change.
- Confirm lint, type, test, and security targets have run; update README or `docs/` when behavior or configuration shifts.

## Security & Configuration Tips

- Store secrets via GitHub OIDC or environment variables; never commit `.env`. Terraform state stays in S3 + Dynamo.
- Validate incoming payloads in backend and parser layers, and protect file writes under `backend/src/data/`.
- Remove debug logging before review and justify any suppressed Bandit rules directly in PR discussions.

## Deployment & Ops

- Dockerfiles per service build minimal images; `compose.yaml` orchestrates backend + frontend containers in dev.
- Terraform under `terraform/` provisions AWS Lightsail and remote state; follow docs in `docs/` for IAM and deployment sequencing.
