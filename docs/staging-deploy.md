# Automated Staging Deployment to AWS App Runner

This repo includes automated deployment to AWS App Runner via GitHub Actions. The workflow builds Docker images, pushes them to ECR, and automatically creates/updates App Runner services.

## What you need in AWS

- An AWS account and a role that GitHub Actions can assume (OIDC) with permissions for ECR and App Runner
- See `docs/aws-iam-permissions.md` for detailed IAM setup

## Files

- `backend/Dockerfile`: FastAPI backend at port 8000 using Uvicorn
- `frontend/Dockerfile`: Flask frontend at port 5000 using Gunicorn, configurable via `BACKEND_URL` env var
- `.github/workflows/push-images.yaml`: Build + push images to ECR + deploy to App Runner (manual trigger)
- `.dockerignore`: Keeps images lean

## Deploy to staging (automated)

1. **Setup GitHub secrets** (one time):

   - `AWS_ACCOUNT_ID`: Your account ID (e.g., 123456789012)
   - `AWS_ROLE_TO_ASSUME`: The IAM role ARN your workflow will assume

2. **Deploy**:

   - Merge your PR to main
   - Go to Actions → "Build and Deploy to AWS Staging" → Run workflow
   - You can override repo names and region if needed (defaults: eu-north-1)

3. **Access your app**:
   - The workflow will output the frontend URL at the end
   - Backend: `https://<random-id>.eu-north-1.awsapprunner.com`
   - Frontend: `https://<random-id>.eu-north-1.awsapprunner.com` (main app URL)

## What the workflow does automatically

1. **Builds and pushes Docker images** to ECR repos:

   - `light-score-backend:staging`
   - `light-score-frontend:staging`

2. **Creates/updates App Runner services**:

   - Backend service: `light-score-backend-staging`
   - Frontend service: `light-score-frontend-staging`
   - Configures ports, health checks, and environment variables
   - Sets up auto-deployment for future updates

3. **Connects frontend to backend** automatically via `BACKEND_URL` environment variable

## Service configuration

- **CPU/Memory**: 0.25 vCPU, 0.5 GB (can be changed in workflow)
- **Health checks**: HTTP on `/` path
- **Auto-deploy**: Enabled (services update when new images are pushed)

## Subsequent deployments

After the first deployment, just run the workflow again - it will:

- Build new images with latest code
- Update existing App Runner services
- Services will automatically restart with new code

## Local development

- Backend: `uv venv && ./scripts/uv-sync.sh --all && .venv/bin/uvicorn backend.src.main:app --reload`
- Frontend: `BACKEND_URL=http://localhost:8000 .venv/bin/python -m flask --app frontend/src/app.py run -p 5000`

Or use: `make dev-setup && make start`

## Notes

- For production, consider using larger instance sizes and implementing proper logging/monitoring
- Database credentials should be stored in AWS Secrets Manager when you add a database
- The App Runner service URLs are stable - they won't change unless you delete and recreate the services
