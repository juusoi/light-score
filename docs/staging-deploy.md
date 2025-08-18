# Staging deployment to AWS (App Runner via ECR)

This repo now includes Dockerfiles for backend and frontend, and a GitHub Actions workflow to build and push images to Amazon ECR for a staging environment.

## What you need in AWS

- An AWS account and a role that GitHub Actions can assume (OIDC) with permissions for ECR and App Runner.
- Two ECR repositories:
  - `light-score-backend` (default)
  - `light-score-frontend` (default)
- Two App Runner services (one per image) or an ECS Fargate setup. App Runner is the simplest to start.

## Files added

- `backend/Dockerfile`: FastAPI backend at port 8000 using Uvicorn.
- `frontend/Dockerfile`: Flask frontend at port 5000 using Gunicorn, configurable via `BACKEND_URL` env var.
- `.github/workflows/push-images.yaml`: Build + push images to ECR (manual trigger).
- `.dockerignore`: Keeps images lean.

## Build and push images (from GitHub Actions)

1. In GitHub repo settings, add secrets:
   - `AWS_ACCOUNT_ID`: Your account ID (e.g., 123456789012)
   - `AWS_ROLE_TO_ASSUME`: The IAM role ARN your workflow will assume
   - (Optional for auto-update) `APP_RUNNER_BACKEND_SERVICE_ARN`, `APP_RUNNER_FRONTEND_SERVICE_ARN`, `STAGING_BACKEND_URL`
2. Run the workflow: Actions → "Build and Push Staging Images" → Run workflow.
   - You can override repo names and region if needed.

## Create App Runner services (once)

Do this once per service via AWS Console or CLI.

### Backend (FastAPI)

- Source: Container image from ECR
- Image: `<account>.dkr.ecr.<region>.amazonaws.com/light-score-backend:staging`
- Port: 8000
- Health check path: `/`
- Auto-deploy: enabled (optional)

### Frontend (Flask)

- Source: Container image from ECR
- Image: `<account>.dkr.ecr.<region>.amazonaws.com/light-score-frontend:staging`
- Port: 5000
- Environment variables:
  - `BACKEND_URL`: Point to the backend service URL (e.g., `https://<apprunner-backend-id>.<region>.awsapprunner.com`)
- Health check path: `/`
- Auto-deploy: enabled (optional)

Once services are running, open the frontend URL; it will call the backend using `BACKEND_URL`.

## Local test

- Backend: `uv venv && ./scripts/uv-sync.sh --all && .venv/bin/uvicorn backend.src.main:app --reload`
- Frontend: `BACKEND_URL=http://localhost:8000 .venv/bin/python -m flask --app frontend/src/app.py run -p 5000`

## Notes

- For ECS instead of App Runner, reuse the ECR images and set up Task Definitions with the same ports and env vars.
- If you later add a database, store credentials in AWS Secrets Manager and inject via App Runner Env Vars.
