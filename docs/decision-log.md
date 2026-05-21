# Decision Log

This log records lightweight architecture/product decisions for the current app.

## DEC-001

- Date: 2026-05-21
- Status: accepted
- Context: The product prioritizes delivery speed and stable backend-rendered pages.
- Decision: Use Flask server-rendered templates for the primary UI surface.
- Consequences: Simpler deploy/debug flow; less client-side app complexity.
- Revisit Trigger: Need for richer client-side state/navigation beyond current patterns.

## DEC-002

- Date: 2026-05-21
- Status: accepted
- Context: Current week navigation requirements are straightforward and URL-driven.
- Decision: Keep week navigation as visible `Prev`/`Next` links.
- Consequences: Predictable behavior and testability; no global keyboard router required.
- Revisit Trigger: Formal requirement for keyboard-first teletext routing.

## DEC-003

- Date: 2026-05-21
- Status: accepted
- Context: Upstream/backend availability can fail and should not blank the UI.
- Decision: Render an explicit offline fallback page on network-level backend failures.
- Consequences: Better user resilience; service degradation is visible but controlled.
- Revisit Trigger: Adoption of alternative offline strategy (cached client state, etc.).

## DEC-004

- Date: 2026-05-21
- Status: accepted
- Context: Postseason data availability is conditional and should not break main flows.
- Decision: Render playoff bracket conditionally inside `/` for `seasonType=3`.
- Consequences: One primary entry route; bracket can gracefully disappear when unavailable.
- Revisit Trigger: Need for dedicated postseason route or view model separation.

## DEC-005

- Date: 2026-05-21
- Status: accepted
- Context: External payload quality is variable and may include malformed/error shapes.
- Decision: Parse backend responses defensively and default to safe empty structures.
- Consequences: Fewer runtime crashes; some failures appear as empty states.
- Revisit Trigger: Introduction of strict schema contracts with hard-fail handling.

## DEC-006

- Date: 2026-05-21
- Status: accepted
- Context: Existing API integrations and clients use camelCase query naming.
- Decision: Preserve `seasonType` externally while using snake_case internally.
- Consequences: Backward compatibility for API consumers; minor naming translation overhead.
- Revisit Trigger: Versioned API migration that permits contract renaming.

## DEC-007

- Date: 2026-05-21
- Status: accepted
- Context: ESPN may return fallback scoreboard data from a different season/week when a requested period has no games yet.
- Decision: Treat `/games/weekly` responses as valid only when returned season/year/week context matches explicit request params.
- Consequences: Prevents stale historical scores from appearing for future navigation targets; empty game lists now represent unavailable periods.
- Revisit Trigger: Upstream API guarantees strict context fidelity or product chooses explicit "nearest available week" behavior.

## DEC-008

- Date: 2026-05-21
- Status: accepted
- Context: GitHub-hosted runners are deprecating older Node runtimes for JavaScript actions, and mutable major tags can shift behavior without a code change in this repo.
- Decision: Update workflow actions to Node 24 compatible releases and pin external actions to full commit SHAs.
- Consequences: Better supply-chain integrity and deterministic CI behavior; routine dependency bump maintenance now requires explicit SHA updates.
- Revisit Trigger: Adoption of an automated action-update bot/policy that centrally manages SHA pin refreshes.

## DEC-009

- Date: 2026-05-21
- Status: accepted
- Context: Type errors should block merges once the baseline is stable; non-blocking checks allow regressions through.
- Decision: Make `ty check` a blocking CI gate and add workflow linting (`actionlint`) to local CI via `just ci`.
- Consequences: Stricter quality gate for PRs; contributors get earlier workflow/type feedback locally.
- Revisit Trigger: Widespread false positives or a toolchain migration away from `ty`/`actionlint`.
