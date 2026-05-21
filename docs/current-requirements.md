# Current Requirements

This document defines the current, test-backed requirements for Light Score.
It is intentionally scoped to what the app does today.

## Scope

- Product scope: NFL weekly scoreboard and standings UI, rendered by Flask.
- Delivery scope: backend data fetch + frontend rendering + graceful fallback behavior.
- This is a baseline for change control, not a roadmap.

## Functional Requirements

### FR-001 Main Page Rendering

- The frontend serves a main page at `/`.
- The page renders Light Score branding and core sections for games data.
- In regular season contexts, the page shows `Live`, `Games`, and `Standings` panels.

### FR-002 Query Parameter Contract

- The frontend accepts `year`, `week`, and `seasonType` query parameters.
- Input values are sanitized to valid integer ranges before forwarding to backend endpoints.
- Invalid query values are ignored rather than causing an app error.

### FR-003 Week Navigation

- Week navigation is link-based (`Prev` and `Next`) on the main page.
- Navigation parameters are sourced from backend navigation data when available.
- If navigation endpoint calls fail, the frontend computes safe local fallback values.

### FR-004 Games Rendering States

- Weekly games are rendered from backend payloads and partitioned into:
  - `live`
  - `final`
  - `upcoming`
- Live games appear in the `Live` panel.
- Final and upcoming games appear in the `Games` panel.

### FR-005 Standings Rendering

- Standings are loaded from live standings first and cache fallback second.
- Standings are grouped by division when division data exists.
- Team ordering within a division is sorted by wins descending, losses ascending, then team name.

### FR-006 Postseason Bracket Behavior

- In postseason context (`seasonType=3`), frontend attempts to fetch bracket data.
- If bracket data is available and valid, a `Playoff Bracket` panel is rendered.
- If bracket data is unavailable, the app degrades safely and still renders the page.

## Resilience Requirements

### RR-001 Offline UI Fallback

- If backend requests fail at network level, frontend renders `home_no_api.html`.
- Offline page remains user-visible and branded instead of returning an application crash.

### RR-002 Defensive Payload Parsing

- Backend responses are parsed defensively.
- Unexpected payload types or error/detail payloads fall back to safe defaults.
- Rendering continues with partial/empty data where necessary.

## UI and Accessibility Baseline

- UI uses teletext-inspired styling and a monospaced presentation.
- Layout is responsive across desktop/tablet/mobile viewports.
- Navigation and key data regions retain basic accessibility semantics (headings, labels, visible links).

## Non-Goals (Current Baseline)

- No strict viewport-locked 4:3 rendering engine.
- No zero-scroll hard input interception model.
- No global 3-digit teletext page router (`P100` style keyboard routing).
- No mandatory fast-text color hotkey engine (`R/G/Y/B`) as a current guarantee.

## Traceability

- Frontend behavior: `frontend/src/app.py`, `frontend/src/templates/home.html`, `frontend/src/templates/home_no_api.html`.
- Frontend unit tests: `frontend/src/utest/test_app.py`.
- E2E behavior checks: `e2e/tests/home.spec.ts`, `e2e/tests/application.spec.ts`, `e2e/tests/playoff-bracket.spec.ts`, `e2e/tests/error-handling.spec.ts`.
- Backend dependency surface: `backend/src/main.py` (`/games/weekly`, `/games/weekly/context`, `/games/weekly/navigation`, `/standings`, `/standings/live`, `/playoffs/bracket`).
