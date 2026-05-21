# AGENTS Guide: light-score

This file is for autonomous coding agents working in this repository.
It captures the build/lint/test workflow and the coding conventions observed in code + config.

## Rule Sources Checked

- `.cursor/rules/`: not present.
- `.cursorrules`: not present.
- `.github/copilot-instructions.md`: not present.
- Therefore, follow this file + repository code/config as the authoritative guidance.

## Architecture Snapshot

- Monorepo with three Python services and one TypeScript E2E test project.
- `backend/`: FastAPI API (`backend/src/main.py`) for games, standings, teams, playoffs.
- `frontend/`: Flask server-rendered UI (`frontend/src/app.py`, Jinja templates in `frontend/src/templates`).
- `functions/`: ESPN parsing/ingestion utilities writing standings cache.
- `e2e/`: Playwright + TypeScript tests against frontend (and local backend when available).
- Shared tooling lives at repo root: `justfile`, root `pyproject.toml`, `.venv` via `uv`.

## Environment & Setup

- Python: 3.13+ required (`requires-python = ">=3.13"`).
- Package/env manager: `uv`.
- Primary setup command:

```bash
just dev-setup
source .venv/bin/activate
```

- Sync deps after changes: `just sync`.
- Container engine defaults to Podman; override with Docker when needed:

```bash
just --set docker docker up
```

## Build / Run Commands

- Build containers: `just build-images`.
- Start services: `just up` (backend `:8000`, frontend `:5000`).
- Stop services: `just down`.
- Tail logs: `just logs`.
- Quick health check: `just health`.
- Mock data mode (no live ESPN dependency): `just mock-up`.

## Lint / Format / Typecheck Commands

- Python lint: `just lint` (`ruff check .`).
- Python format: `just fmt` (`ruff format .`).
- Python type checks: `just ty` (`ty check .`).
- Full Python CI bundle: `just ci` (lint + types + unit tests).
- Security checks: `just security` (Bandit + pip-audit).

## Python Test Commands

- All Python unit tests: `just test`.
- Backend-only suite:

```bash
cd backend/src && ../../.venv/bin/python -m pytest utest/ -v
```

- Other service suites use the same pattern from project root:
  - `cd frontend/src && ../../.venv/bin/python -m pytest utest/ -v`
  - `cd functions/src && ../../.venv/bin/python -m pytest utest/ -v`

- Run a single test file (example):

```bash
cd backend/src && ../../.venv/bin/python -m pytest utest/test_navigation.py -v
```

- Run a single test function (example):

```bash
cd backend/src && ../../.venv/bin/python -m pytest utest/test_main.py::test_get_weekly_games -v
```

- Filter tests by name pattern:

```bash
cd frontend/src && ../../.venv/bin/python -m pytest utest/ -k "offline or navigation" -v
```

## E2E (Playwright / TypeScript) Commands

- Install E2E deps (if needed): `cd e2e && bun install`.
- E2E lint: `just lint-e2e`.
- E2E format: `just fmt-e2e`.
- E2E type check: `just ty-e2e`.
- E2E CI tests: `just test-e2e` (runs `bun run test:ci`).
- Run a single E2E spec:

```bash
cd e2e && bun run test -- tests/home.spec.ts
```

- Run a single E2E test title:

```bash
cd e2e && bun run test -- -g "navigation"
```

## Repository-Specific Coding Rules

- Keep tests deterministic; do not rely on live ESPN/network in unit tests.
- Prefer mocking `httpx.get` in backend tests and `requests.get` in frontend tests.
- Preserve API query parameter naming in camelCase (`seasonType`) for external/API compatibility.
- Preserve Python internal naming in snake_case.
- Keep standings cache schema stable for backend consumers.
- Do not remove stale-cache fallback behavior in backend fetch flows.

## Python Style Guidelines

- Formatter/linter authority: Ruff (configured in root `pyproject.toml`).
- Line length target: 99 chars (Ruff default unless overridden by tool).
- Imports:
  - Group as stdlib, third-party, local.
  - Prefer absolute imports; use relative imports in tests where already established.
  - Avoid wildcard imports.
- Naming:
  - Modules/functions/variables: `snake_case`.
  - Classes/Pydantic models: `PascalCase`.
  - Constants/env defaults: `UPPER_SNAKE_CASE`.
- Types:
  - Use modern annotations (`str | None`, `list[dict]`) on new code.
  - Add explicit return types for non-trivial functions.
  - Keep models typed with Pydantic `BaseModel` where payload contracts matter.
- Data handling:
  - Parse external payloads defensively (`.get`, type checks, fallback defaults).
  - Keep template-facing data JSON-serializable.
  - Normalize external API payloads before returning to clients/templates.
- Error handling:
  - Catch narrow exceptions where practical (`ValueError`, `TypeError`, request exceptions).
  - Use graceful degradation and fallback responses over crashes.
  - In FastAPI routes, use `HTTPException` for client-visible errors.
  - In frontend route handlers, prefer rendering fallback template over raising.
- Logging:
  - Use `logging` (not `print`) for runtime diagnostics.
  - Keep logs concise and actionable; avoid noisy debug logs in committed code.

## TypeScript E2E Style Guidelines

- ESLint + Prettier are the style sources for `e2e/tests/**/*.ts`.
- Prettier defaults: single quotes, semicolons, trailing commas, print width 80.
- Prefer Playwright role/text locators (`getByRole`, `getByText`) and web-first assertions.
- Avoid hard waits; use Playwright auto-waiting assertions.
- Keep tests feature-focused in `*.spec.ts`; place API specs under `e2e/tests/api/`.

## Change Management Expectations

- Keep changes scoped; avoid unrelated refactors.
- Update tests in the same PR as behavior changes.
- **Mandatory Pre-Commit and Pre-Push Checks**: Before committing or pushing any changes to a remote branch, you MUST run all linting, formatting, type checking, and test suites locally to verify your changes. Pushing unformatted or unchecked code that fails remote CI is strictly unacceptable. Use the following checklist:
  - **Python Services**:
    - Run formatting FIRST to ensure all modified code aligns with styling requirements: `just fmt`
    - Run linting: `just lint`
    - Run type checks: `just ty`
    - Run unit tests: `just test`
    - Or run the complete Python CI bundle: `just ci` (covers lint, formatting, type check, and tests)
  - **TypeScript / E2E Projects**:
    - Run E2E formatting: `just fmt-e2e`
    - Run E2E linting: `just lint-e2e`
    - Run E2E type check: `just ty-e2e`
- Never commit secrets or `.env` files.
