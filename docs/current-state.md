# Current State

This document captures the implementation state of Light Score as of today.
It describes what exists in code and tests, without proposing redesign work.

## Architecture Snapshot

- Monorepo with:
  - `backend/` FastAPI API for games, standings, navigation, playoff data.
  - `frontend/` Flask + Jinja web UI.
  - `functions/` data parsing/caching support utilities.
  - `e2e/` Playwright TypeScript tests.
- Frontend and backend run independently and communicate over HTTP.

## Runtime Flow

1. Browser requests `/` from Flask frontend.
2. Frontend sanitizes `year`, `week`, `seasonType` query params.
3. Frontend fetches:
   - `/games/weekly`
   - `/games/weekly/context`
   - `/standings/live` (fallback to `/standings`)
4. Frontend fetches `/games/weekly/navigation` for prev/next links.
5. If `seasonType=3`, frontend optionally fetches `/playoffs/bracket`.
6. Frontend renders `home.html` or `home_no_api.html` on network failure.

## Frontend State

- Entry point: `frontend/src/app.py`.
- Main route: `/`.
- Templates currently in use:
  - `frontend/src/templates/home.html`
  - `frontend/src/templates/home_no_api.html`
- Static styling: `frontend/src/static/teletext.css`.

Current UI behavior:

- Header shows season context and week navigation links.
- `Live` panel shows in-progress games or empty-state message.
- `Games` panel shows final/upcoming games with status-specific rendering.
- Regular season path renders standings grouped by division.
- Postseason path renders playoff bracket when bracket data is available.

## Backend Dependency Surface Used by Frontend

- `/games/weekly`
- `/games/weekly/context`
- `/games/weekly/navigation`
- `/standings/live`
- `/standings`
- `/playoffs/bracket`

## Data/State Handling Details

- Query values are parsed defensively and bounded to accepted ranges.
- Weekly games are filtered to valid records before rendering.
- Games are split into `history`, `live`, and `upcoming` arrays.
- Standings are grouped by division and sorted by record.
- Navigation has both endpoint-driven and local fallback behavior.
- Postseason bracket is conditional and non-fatal if unavailable.

## Error and Degradation Behavior

- Network-level request failures produce `home_no_api.html`.
- Malformed JSON or incompatible payloads resolve to safe defaults.
- Non-OK upstream responses trigger retries/fallback paths where implemented.

## Test Coverage Signals

- Frontend unit tests verify:
  - main route rendering
  - query/nav behavior
  - offline fallback page
  - postseason bracket panel path
- E2E tests verify:
  - core page structure and branding
  - week navigation links and interactions
  - standings and game state display behaviors
  - postseason bracket UI structure
  - basic responsiveness/accessibility expectations

## Known Documentation Drift Resolved in This Pass

- Frontend documentation had references to `/playoffs` and `playoffs.html` that do not
  match current frontend route/template implementation.
- Canonical behavior is now tracked in:
  - `docs/current-requirements.md`
  - `docs/current-state.md`
  - `docs/decision-log.md`
