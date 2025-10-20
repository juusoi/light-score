# Repository Guidelines

## Project Structure & Module Organization

- `backend/src` hosts the FastAPI service (`main.py` entrypoint); add domain modules under descriptive subpackages and keep JSON caches in `data/`.
- `frontend/src` contains the Flask UI with `templates/` and `static/`; route helpers live beside the app factory.
- `functions/src` holds ESPN parsing jobs; trigger ad-hoc refreshes with `python functions/src/main.py`.
- Co-locate unit tests under each `src/utest/` package; store higher-level smoke flows in `e2e/`. Reference operational notes in `docs/`, automation in `scripts/`, and infrastructure in `terraform/`.

## Build, Test, and Development Commands

- `make dev-setup` installs uv, resolves dependencies, and bootstraps `.venv`.
- `make up` / `make down` start and stop the backend (`:8000`) and frontend (`:5000`) containers; `make build-images` rebuilds when dependencies shift.
- `make test` executes pytest across all packages; `make ci` runs lint, types, and tests in one pass.
- `make lint fmt ty` applies Ruff linting, formatting, and `ty` type checks; `make security` runs Bandit plus pip-audit; `make health` performs a quick API smoke.

## Coding Style & Naming Conventions

- Python 3.13+ with uv-managed virtualenv; use absolute imports and module-level constants for shared configuration.
- Follow Ruff defaults: four-space indentation, 99-character lines, snake_case modules, and descriptive function names.
- Name FastAPI paths with nouns (`/scores`, `/standings`) and align Flask templates with their routes (`templates/scores.html`).
- Run `make fmt` before committing to keep formatting clean.

## Testing Guidelines

- Write pytest tests named `test_*` inside the closest `src/utest/`; isolate fixtures under `utest/fixtures/`.
- Mock external HTTP calls with `httpx` mock transports or local sample payloads—no live ESPN traffic in CI.
- Keep tests deterministic and fast; ensure `make test` and `make ci` pass locally before pushing.

## Commit & Pull Request Guidelines

- Use Conventional Commits (e.g., `feat: add standings endpoint`) with ≤72-character summaries and focused scope.
- Link issues, document manual checks, and attach screenshots or curl snippets when UI or API responses change.
- Confirm lint, type, test, and security targets have run; update README or `docs/` when behavior or configuration shifts.

## Security & Configuration Tips

- Store secrets via GitHub OIDC or environment variables; never commit `.env`. Terraform state stays in S3 + Dynamo.
- Validate incoming payloads in backend and parser layers, and protect file writes under `functions/src/data/`.
- Remove debug logging before review and justify any suppressed Bandit rules directly in PR discussions.
