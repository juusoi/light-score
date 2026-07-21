# Plan: Calendar-Driven Season Default Resolution

Status: **proposal / thinking doc** — not yet implemented.
Author context: raised from the observation that the frontpage defaults to Regular
Season even though Preseason comes first chronologically.

Related docs: [`navigation.md`](../navigation.md), [`season-history.md`](../season-history.md),
[`decision-log.md`](../decision-log.md).

---

## 1. Problem

When a user loads `/` with no query parameters, the platform shows whatever ESPN's
bare scoreboard call reports as "current." Two issues fall out of this:

1. **Preseason is skipped.** In the off-season (verified 2026-07-21), ESPN's no-param
   scoreboard already returns `season.type = 2` (Regular Season), week 1 — pointing at
   the September opener even though Preseason games (Aug 6+) happen first. So the
   landing view jumps past Preseason entirely, and there is no guarantee ESPN's bare
   default ever flips to Preseason during the Aug 6 – Sep 9 window.

2. **The season year is hardcoded.** Per `season-history.md`, the default year is a
   hardcoded constant (`2026`) in both `backend/src/main.py` and
   `frontend/src/app.py`, with a manual "rollover checklist" to bump it each year.
   This is maintenance debt and a recurring source of drift.

Both problems share a root cause: **we treat ESPN's bare default as the source of
truth for "what season/week is current," when ESPN actually publishes a richer,
authoritative signal we're not using.**

---

## 2. Key findings (from live ESPN, 2026-07-21)

The scoreboard payload includes `leagues[0].calendar` — an authoritative, per-season
breakdown with **nested per-week windows**. Shape:

```
calendar[]                      # one entry per season type
  label      "Preseason"
  value      "1"
  startDate  2026-08-06T07:00Z
  endDate    2026-09-09T06:59Z
  entries[]                     # one entry per week within that type
    label     "Hall of Fame Weekend"
    value     "1"
    startDate 2026-08-06T07:00Z
    endDate   2026-08-13T06:59Z
```

2026 season windows as reported by ESPN:

| type | season         | window                          |
|------|----------------|---------------------------------|
| 1    | Preseason      | 2026-08-06 → 2026-09-09         |
| 2    | Regular Season | 2026-09-09 → 2027-01-13         |
| 3    | Postseason     | 2027-01-13 → 2027-02-16         |
| 4    | Off Season     | 2027-02-16 → 2027-08-01         |

**Critical gotcha:** `?seasontype=1` *alone* is ignored by ESPN — it still returns
type 2 / week 1. To actually fetch a specific season/week you must send
`dates=<year>` **and** `seasontype=<type>` **and** `week=<n>` together. This is the
same class of bug already fixed for `dates=` vs `year=` (commit `848967e`).

**Implication:** because ESPN republishes these windows every season, reading the
calendar is inherently **year-agnostic** — 2027 and beyond work with no code change
and no hardcoded dates.

---

## 3. Proposed design

Introduce a pure resolver and use it **only on the no-explicit-`seasonType` path**.

```
_resolve_current_from_calendar(calendar, now_utc) -> (year, seasonType, week)
```

- Find the type-entry whose `[startDate, endDate)` contains `now_utc`; within it, find
  the week-entry containing `now_utc`. Return `(year, type, week)`.
- **Off Season (type 4):** no games exist and the app only accepts types 1/2/3, so
  fall back to the *upcoming* Preseason week 1 — which is exactly the "preseason comes
  first" intent.

Wiring:

- `backend/src/main.py`:
  - `get_weekly_context` and `_get_weekly_games`, when no `seasonType` is requested,
    call the resolver against the calendar from the initial no-param scoreboard, then
    refetch with `dates` + `seasontype` + `week` (per the gotcha above).
- Explicit `?year=&seasonType=&week=` requests **bypass the resolver entirely** —
  archived/manual navigation behaviour is unchanged.
- Frontend untouched.

Properties:

- **Year-agnostic / self-maintaining** — no date or year literals; ESPN's windows
  drive everything.
- **No ESPN-vs-us conflict** — we use ESPN's own authoritative calendar, not a guess
  that overrides it.
- **Deterministic & testable** — resolver is pure `(calendar, now) → (type, week,
  year)`; unit-test with a captured calendar fixture and fixed `now` values (one per
  window boundary + off-season).

---

## 4. Relationship to the hardcoded-year policy

This design makes the **"Season Rollover Checklist"** and **"2027 Flip Checklist"** in
`season-history.md` largely obsolete for the *live* path: the current year comes from
the calendar, not a constant.

Decision needed (see open questions): do we
- (a) keep the hardcoded constants purely as **offline/`MOCK_ESPN` fallbacks** (when
  the calendar is unavailable), and delete them from the live path; or
- (b) leave the constants in place and layer the resolver on top?

Recommendation: **(a)** — the constant becomes a last-resort fallback only, and
`season-history.md` is updated to say the live default is calendar-derived.

---

## 5. Bigger picture (for you to weigh)

These are intentionally out of scope for the first change but shape whether the design
above is the right foundation.

### 5.1 Archived / past seasons
- Today, past seasons are reachable only by hand-editing `?year=` in the URL. The
  resolver doesn't help discovery — it only answers "what is current."
- **Open question:** do we want a season picker / archive index (e.g. a dropdown of
  past years, or a `/seasons` page)? If so, where does the list of valid archived
  years come from — a static lower bound (ESPN data availability) up to the current
  calendar year? ESPN's calendar is per *current* season and won't enumerate history.
- The resolver is compatible either way: explicit year requests already bypass it.

### 5.2 Navigation continuity
- `navigation.md` §3 already defines prev/next transitions across type boundaries
  (Preseason wk4 → Regular wk1, etc.) using **hardcoded week limits** (pre 1–4, reg
  1–18, post 1–4). Once we trust ESPN's calendar for the *default*, there's an
  inconsistency: navigation limits are still hardcoded while defaults are dynamic.
- **Open question:** should navigation limits also derive from the calendar's
  per-week entries (fully dynamic, handles an 18- vs 17-game era, extra playoff
  rounds, international weeks), or is the hardcoded ladder good enough? Dynamic
  navigation is a bigger change and probably a separate plan.

### 5.3 Off-season landing
- With the resolver, off-season (type 4) lands on upcoming Preseason wk1. Confirm this
  is desired vs. e.g. showing the just-finished postseason, or a "season starts in N
  days" state.

### 5.4 Mock-mode fidelity
- `navigation.md` §4.II requires mock mode to only serve fixture-backed weeks. There
  is no preseason fixture today (`backend/src/fixtures/` has regular + postseason
  only). If the resolver ever runs in mock mode, decide: add a `preseason.json`
  fixture, or keep the resolver live-only and let mock mode use the constant default.

---

## 6. Edge cases & invariants

- **Boundary instants:** windows are half-open `[start, end)`; a timestamp exactly on
  a boundary belongs to the later window. Test the exact `endDate`/`startDate` seams.
- **Timezone:** ESPN windows are UTC (`Z`); resolver must compare in UTC, not local.
- **Malformed / missing calendar:** if `calendar` is absent or unparseable, fall back
  to the existing constant default and log — never 500 the frontpage.
- **Explicit requests are authoritative** (unchanged): resolver never overrides a
  user-supplied `seasonType`.
- **Mismatch prevention** (`navigation.md` §4.I) still holds: a resolved refetch that
  fails must not silently render another week.

---

## 7. Testing strategy

- Unit-test `_resolve_current_from_calendar` with a captured 2026 calendar fixture:
  - a `now` inside each of preseason/regular/postseason → correct (type, week, year)
  - a `now` in off-season → upcoming preseason wk1
  - boundary seams (exact start/end)
  - missing/garbled calendar → constant fallback
- Integration: no-param `/games/weekly/context` returns the resolved context; explicit
  params still bypass the resolver.
- Capture a real calendar fixture (`backend/src/fixtures/calendar_2026.json` or
  similar) so tests don't hit the network.

---

## 8. Decisions to confirm before implementing

1. Adopt calendar-driven default? (core of this plan)
2. Constants → offline-only fallback (§4 option a) vs. keep alongside (b)?
3. Off-season landing = upcoming preseason wk1? (§5.3)
4. Scope: is archived-season discovery (§5.1) and dynamic navigation limits (§5.2)
   in this effort, or separate follow-up plans? (recommendation: separate)
5. Mock-mode handling (§5.4): add preseason fixture, or keep resolver live-only?
