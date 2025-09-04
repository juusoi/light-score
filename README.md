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

Use Make targets (wraps uv + deps):

```bash
make dev-setup
source .venv/bin/activate
```

## Run (local)

Containers (Podman default; set DOCKER=docker to use Docker):

```bash
make build-images    # build images (or runs implicitly if stale)
make up              # backend:8000 frontend:5000
```

Parser (standings cache) manually:

```bash
python functions/src/main.py
```

Stop containers:

```bash
make down
```

## Tests

```bash
make test
```

## Lint / Format / Types / Security

```bash
make lint fmt ty
make security    # bandit + pip-audit
```

`make ci` runs lint + ty + test.

## Deployment

CI → Security → Deploy (Lightsail). Terraform remote state (S3 + Dynamo, prefix scoped). Images built & pushed with `lightsailctl`; `BACKEND_URL` set to internal DNS. See `docs/aws-iam-permissions.md`.

## Secrets

GitHub: `AWS_ROLE_TO_ASSUME` (OIDC). No static AWS keys.

## Placeholders

Docs use ALL_CAPS (ACCOUNT_ID, TF_STATE_BUCKET, TF_LOCKS_TABLE, etc.).

## License

MIT (see `LICENSE`).

## Quick Targets

| Task             | Command             |
| ---------------- | ------------------- |
| Setup env        | `make dev-setup`    |
| Build images     | `make build-images` |
| Run (containers) | `make up`           |
| Stop containers  | `make down`         |
| Lint / Format    | `make lint fmt`     |
| Types            | `make ty`           |
| Tests            | `make test`         |
| Full CI locally  | `make ci`           |
| Security scan    | `make security`     |
| Health check     | `make health`       |
| Cleanup          | `make clean`        |
