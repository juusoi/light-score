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

## DEC-010

- Date: 2026-06-24
- Status: accepted
- Context: CI's type-check step runs `ty` with `PYTHONPATH=backend/src:frontend/src:functions/src`, which makes `..main` imports in backend tests unresolvable (hence their `# ty: ignore[unresolved-import]` directives). The local `just ty` recipe omitted that PYTHONPATH, so `just ci` and CI disagreed: each could pass while the other failed.
- Decision: Set the same `PYTHONPATH` in the `just ty` recipe so local type checks reproduce the CI gate exactly. Keep the `# ty: ignore[unresolved-import]` directives, which are required under that path layout.
- Consequences: `just ci` is now a faithful local mirror of the CI type-check gate; the divergence that let mismatched changes slip through is closed.
- Revisit Trigger: Restructuring the type-check path layout (e.g. dropping the CLI `PYTHONPATH` in favor of a `[tool.ty]` config) so the ignore directives are no longer needed.

## DEC-011

- Date: 2026-09-15
- Status: accepted
- Context: Deploying on an affordable 1 vCPU / 1 GB RAM UpCloud Ubuntu cloud server requires minimizing hosting costs, keeping memory usage well below 1 GB, and avoiding CPU/OOM spikes during deployment. At the same time, existing AWS Lightsail infrastructure must remain untouched during the transition for zero-downtime cutover and instant rollback.
- Decision: Lift and shift the container stack to UpCloud using rootless Podman Quadlets (`deployer` user with linger enabled) with pull-based `podman auto-update` behind Caddy for automated TLS. Offload all container builds and layer caching to GitHub Actions pushing to GHCR (`ghcr.io`). The server runs `podman-auto-update.timer` to automatically detect new digests and restart units, requiring zero SSH keys or deploy credentials in GitHub Secrets and exposing zero inbound ports for CI/CD. Frontend binds strictly to `127.0.0.1:5000` while backend is internal on `light-score-net`.
- Consequences: Total stack runtime footprint is ~150-180 MB, well within the 1 GB RAM budget. No OOM risk on the server. Zero credential exposure in CI. Built-in rollback via Podman if a new image fails. Lightsail continues operating as a warm standby until DNS cutover and validation are complete.
- Revisit Trigger: Upgrading server hardware, transitioning to multi-node orchestration, or completing the final decommissioning of Lightsail.

## DEC-012

- Date: 2026-09-15
- Status: accepted
- Context: Following successful DNS cutover and verification of the UpCloud production environment, the AWS Lightsail container service was deleted via the AWS CLI. The legacy AWS deployment workflow (`deploy-lightsail.yaml`) and AWS IAM/Terraform infrastructure are now obsolete.
- Decision: Decommission AWS Lightsail infrastructure permanently and retire `.github/workflows/deploy-lightsail.yaml`. The sole deployment pipeline is now `.github/workflows/push-ghcr.yaml` publishing to GHCR, with pull-based Podman Quadlet auto-updates on the UpCloud server. Update repository documentation, Caddy configuration, and deployment guides to reflect the active production architecture.
- Consequences: AWS billing for Lightsail is eliminated. CI/CD workflow is simplified with zero external cloud deployment credentials needed in GitHub. Reduced maintenance overhead and smaller attack surface.
- Revisit Trigger: Migration to a different hosting provider or orchestrator.

## DEC-013

- Date: 2026-09-17
- Status: accepted
- Context: Containers lacked health checks, and rootless Podman Quadlets had no readiness signaling. Under default Podman behavior, systemd marks containers "active" immediately upon process spawn, causing `podman auto-update` to treat broken deployments as successful and preventing automatic rollback. Furthermore, frontend health probes hitting `/` incurred full HTML template rendering and backend API roundtrips.
- Decision: Add dedicated lightweight `/health` JSON endpoints to both backend and frontend. Install `curl` and declare `HEALTHCHECK` directives in `backend/Dockerfile` and `frontend/Dockerfile`. Configure `Notify=healthy`, `HealthCmd`, `HealthOnFailure=kill`, and `TimeoutStartSec=60` on Quadlet container units. Add `healthcheck` specifications to `compose.yaml` and `compose.prod.yaml`.
- Consequences: `podman auto-update` now reliably verifies application responsiveness before committing updates. If a newly pulled image from GHCR fails its health check within `TimeoutStartSec=60`, systemd marks the restart as failed, and Podman automatically rolls back to the prior working image from GHCR with zero downtime. Runtime container stalls trigger automatic restart via `HealthOnFailure=kill`. Health probes are lightweight and isolated from external API dependencies.
- Revisit Trigger: Transition to Kubernetes/orchestrator with custom readiness/liveness probes or introduction of external synthetic monitoring probes.



