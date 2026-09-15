# Deployment

Production deployment runs on an UpCloud Ubuntu Cloud Server using pull-based Rootless Podman Quadlets and Caddy.

See [docs/deploy-upcloud.md](file:///Users/juuso/code/juusoi/light-score/docs/deploy-upcloud.md) for full architecture and operation details.

## Workflow

1. Push to `main` → CI & Security workflows run and pass.
2. `push-ghcr.yaml` builds multi-stage images and pushes to GitHub Container Registry (`ghcr.io/juusoi/light-score-*`).
3. UpCloud server's `podman-auto-update.timer` polls for new digests, pulls images, and restarts the services automatically with zero downtime.

## Local Development

Backend:
```bash
uvicorn backend.src.main:app --reload --port 8000
```

Frontend:
```bash
BACKEND_URL=http://localhost:8000 flask --app frontend/src/app.py run -p 5000
```

Or via containers:
```bash
just up
# or with mock data:
just mock-up
```

## Legacy Deployment

AWS Lightsail deployment has been decommissioned as of 2026-09-15 (see `docs/decision-log.md` DEC-011 and DEC-012).
