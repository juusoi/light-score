# Light Score

FastAPI backend + Flask frontend + parser functions (ESPN standings/games). Deployed to AWS Lightsail via Terraform + GitHub Actions OIDC (no static keys).

## Structure

`backend/` API  
`frontend/` UI  
`functions/` data parsing  
`scripts/` automation  
`docs/` concise ops + IAM

## Requirements

Python 3.13+, uv.

## Setup

Use just recipes (wraps uv + deps):

```bash
just dev-setup
source .venv/bin/activate
```

## Run (local)

Containers (Podman default; set DOCKER=docker to use Docker):

```bash
just build-images    # build images (or runs implicitly if stale)
just up              # backend:8000 frontend:5000
```

### Mock Mode (Development)

Run with mock ESPN data for testing playoff brackets and standings:

```bash
just mock-up         # backend:8000 frontend:5000 with mock data
```

Access mock views:
- Regular season: `http://localhost:5000/?seasonType=2`
- Postseason: `http://localhost:5000/?seasonType=3`

Parser (standings cache) manually:

```bash
python functions/src/main.py
```

Stop containers:

```bash
just down
```

## Tests

```bash
just test
```

## Lint / Format / Types / Security

```bash
just lint fmt ty
just lint-actions
just security    # bandit + pip-audit
```

`just ci` runs lint + Actions lint + ty + test.

## Deployment

CI → Security → Deploy (Lightsail). Terraform remote state (S3 + Dynamo, prefix scoped). Images built & pushed with `lightsailctl`; `BACKEND_URL` set to internal DNS. See `docs/aws-iam-permissions.md`.

## Canonical Product Docs

- Current requirements: `docs/current-requirements.md`
- Current implementation state: `docs/current-state.md`
- Decision log: `docs/decision-log.md`

## Secrets

GitHub: `AWS_ROLE_TO_ASSUME` (OIDC). No static AWS keys.

## Placeholders

Docs use ALL_CAPS (ACCOUNT_ID, TF_STATE_BUCKET, TF_LOCKS_TABLE, etc.).

## License

MIT (see `LICENSE`).

## Quick Targets

| Task             | Command             |
| ---------------- | ------------------- |
| Setup env        | `just dev-setup`    |
| Build images     | `just build-images` |
| Run (containers) | `just up`           |
| Run (mock data)  | `just mock-up`      |
| Stop containers  | `just down`         |
| Lint / Format    | `just lint fmt`     |
| Actions lint     | `just lint-actions` |
| Types            | `just ty`           |
| Tests            | `just test`         |
| E2E Tests        | `just test-e2e`     |
| Full CI locally  | `just ci`           |
| E2E CI           | `just ci-e2e`       |
| Security scan    | `just security`     |
| Health check     | `just health`       |
| Cleanup          | `just clean`        |
