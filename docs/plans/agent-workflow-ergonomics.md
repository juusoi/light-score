# Future Work: Agent Workflow Ergonomics & Hooks

Status: **Reminder / Backlog** (not yet designed or scheduled)

## Context

During feature work, coding agents currently have to compose ad-hoc shell commands to spin up local mock servers, run single Playwright specs without hanging on interactive HTML reports, or work around tooling quirks. Several routine verification checks could also be enforced automatically via hooks rather than relying on manual command chains.

## Ideas to Refactor Later

- **First-class `just` recipes for agent/dev inner loops**:
  - Dedicated recipe to run a single Playwright E2E spec against a self-contained ephemeral mock backend + frontend (with clean startup/teardown, `CI=true` / non-interactive reporter, and local browser selection).
  - Dedicated recipe to capture desktop/mobile UI screenshots against mock mode without ad-hoc bash wrappers.
- **Deterministic offline unit test suite**:
  - Fix or separate `backend/src/utest/test_main.py` tests that currently hit live ESPN when `MOCK_ESPN` is unset (`test_get_weekly_games`, `test_weekly_games_timezone_fields`), so `just test` passes deterministically offline and inside sandboxes.
- **E2E TypeScript / `pnpm` consistency**:
  - Fix `e2e/tsconfig.json` `"types": ["playwright/test", "node"]` vs `@playwright/test` in `e2e/package.json` so `just ty-e2e` passes reliably with default strict `pnpm` installs without requiring `--shamefully-hoist`.
- **Automated hooks**:
  - Evaluate pre-commit / agent hooks for automatic formatting (`ruff format`, `prettier`), linting (`ruff check`, `eslint`), type checking (`just ty`), and secret/diff hygiene checks.
- **Document canonical entrypoints in `AGENTS.md`**:
  - Point agents directly to the standardized `just` recipes and hooks so they never invent one-off wrapper scripts.
