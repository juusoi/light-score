# NFL Season Navigation Specifications

This document defines the requirements, parameters, transitions, and resiliency invariants of the season and week navigation within the Light Score platform.

---

## 1. Context & Domain Structure

The NFL season follows a structured calendar spanning two calendar years (September of Year N to February of Year N+1). The platform categorizes a season into three distinct types:

1. **Preseason (`seasonType` = 1)**: Weeks 1–4
2. **Regular Season (`seasonType` = 2)**: Weeks 1–18
3. **Postseason (`seasonType` = 3)**: Weeks 1–4
   - **Week 1**: Wild Card Round
   - **Week 2**: Divisional Round
   - **Week 3**: Conference Championships
   - **Week 4**: Super Bowl

---

## 2. Navigation State Propagation

### Frontpage Defaults
When a user accesses the root frontpage (`/`) without explicit query parameters:
1. The platform resolves the **current active week** using the `/games/weekly/context` endpoint.
2. The UI renders the current week's scoreboard and the standings.
3. The `Prev` and `Next` links are dynamically rendered pointing to the exact `year`, `week`, and `seasonType` parameters of the adjacent weeks.

### Explicit Parameter Routing
Once a user clicks `Prev` or `Next`, they transition to an explicit parameter route:
- Format: `/?year=<year>&seasonType=<type>&week=<week>`
- The frontend MUST parse and validate these parameters defensively, forwarding them to `/games/weekly` and `/standings/live` to ensure consistent data views.

---

## 3. Smart Week Transitions

The backend `/games/weekly/navigation` endpoint computes the adjacent weeks using the following rules:

### A. Next Direction (`direction` = "next")
* **Within Limits**: If the current week is less than the maximum week for the active season type, increment the week by 1 (retaining the same year and season type).
* **Preseason End**: If week is 4, transition to **Regular Season Week 1** of the same year.
* **Regular Season End**: If week is 18, transition to **Postseason Week 1** of the same year.
* **Postseason End**: If week is 4 (Super Bowl), transition to **Preseason Week 1 of the next calendar year** (`year + 1`).

### B. Prev Direction (`direction` = "prev")
* **Within Limits**: If the current week is greater than the minimum week (Week 1), decrement the week by 1.
* **Preseason Start**: If week is 1, transition to **Postseason Week 4 of the previous calendar year** (`year - 1`).
* **Regular Season Start**: If week is 1, transition to **Preseason Week 4** of the same year.
* **Postseason Start**: If week is 1, transition to **Regular Season Week 18** of the same year.

---

## 4. Architectural Invariants

### I. Mismatched Fallback Prevention
To ensure a consistent user experience, the UI must never show a mismatched state (e.g., displaying the header for "Week 16" but showing the cached or default games of "Week 15").

* **Constraint**: If a request to fetch games for an explicit `year`, `week`, and `seasonType` fails (e.g., ESPN API returns an error or is unreachable for that historical/future date), the frontend **must not** silently retry without parameters.
* **Action**: In case of a backend error for a specific week, the frontend should display a clean error layout or the offline page rather than showing stale results under a different week's title.

### II. Mock Mode Fidelity
Mock mode runs against static JSON fixtures stored in `backend/src/fixtures/`.
* **Constraint**: When `MOCK_ESPN` is active, the backend should only return game scores for the exact weeks represented by our fixture database.
  - Regular Season: Week 15 (defined in `regular_season.json`).
  - Postseason: Weeks 1–4 (defined in `postseason_*.json`).
* **Action**: If a user navigates to any other week (e.g., Week 14 or 16) in mock mode, the API must return an empty list `[]` instead of defaulting to `regular_season.json` (which contains Week 15 games). This prevents the UI from showing mismatched Week 15 games under other week headers.
