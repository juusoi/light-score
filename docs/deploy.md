# Deployment (Lightsail)

## Workflow

CI → Security → Deploy (Lightsail container service). Images built, pushed via `lightsailctl`, deployed with health wait.

## Prerequisites

- OIDC role (`AWS_ROLE_TO_ASSUME`) with required policy
- Terraform applied (service exists or created idempotently)

## Deploy

Merge to main triggers pipeline after security workflow success.

## Backend ↔ Frontend

`BACKEND_URL` injected as `http://LIGHTSAIL_SERVICE_NAME.service.local:8000`.

## Local

Backend:

```
uvicorn backend.src.main:app --reload --port 8000
```

Frontend:

```
BACKEND_URL=http://localhost:8000 flask --app frontend/src/app.py run -p 5000
```

## Troubleshooting

- Quota: delete unused container services
- 403 state: check S3 key matches policy prefix
- Connectivity: verify internal DNS pattern or fallback to 127.0.0.1
