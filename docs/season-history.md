# Season History

This document tracks season-rollover decisions and checks for Light Score.

## Timeline

- **2025 season prep**
  - Introduced explicit season parameter handling and offseason-safe standings behavior.
  - Reduced UI mismatch risk by preserving requested navigation context.

- **2026 season prep**
  - Default context year moved to `2026` in backend weekly context fallback logic.
  - Frontend default context year moved to `2026`.
  - Tests updated to assert a default year of `2026`.
  - Strict mock-week matching retained so unsupported mock weeks do not show mismatched data.

## Current Policy

- **Default season year is hardcoded** for active season readiness.
- Hardcoded default is currently `2026`.
- Requested query parameters (`year`, `week`, `seasonType`) remain authoritative when provided.
- Mock mode must return only fixture-backed weeks; unsupported weeks should not silently map to another fixture.

## Offseason Edge Cases

- **Requested week with unavailable upstream data**
  - Do not silently render a different week's data.
  - Prefer error/offline rendering to avoid UI-context mismatch.

- **Future or unstarted season standings**
  - Preserve explicit year handling and offseason-safe output behavior.

- **Mock mode navigation beyond fixture coverage**
  - Return empty games/context fallback for requested week rather than defaulting to a different fixture week.

## Season Rollover Checklist

Run this when flipping to a new season year.

1. Update hardcoded default season year in:
   - `backend/src/main.py` (weekly context defaults/fallbacks)
   - `frontend/src/app.py` (`DEFAULT_CONTEXT`)
2. Update year-dependent tests:
   - `backend/src/utest/test_main.py`
   - Any frontend tests asserting default context year
3. Run full verification:
   - `just fmt`
   - `just lint`
   - `just ty`
   - `just test`
4. Smoke-check manual flows:
   - Frontpage default load
   - Week navigation prev/next
   - Mock mode unsupported week behavior

## 2027 Flip Checklist

Use this exact mini-checklist for the next rollover:

1. Change default year constants from `2026` to `2027`.
2. Update tests that expect `2026` defaults.
3. Run `just fmt && just lint && just ty && just test`.
4. Verify:
   - `/?year=2027&seasonType=2&week=1`
   - `/?year=2027&seasonType=3&week=1`
   - mock mode week outside fixture coverage returns no mismatched games.
