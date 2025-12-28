# Deployment (Hetzner k3s)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Hetzner Cloud                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   k3s Cluster                         │  │
│  │                                                       │  │
│  │  ┌─────────────┐    ┌─────────────┐                   │  │
│  │  │  Frontend   │────│   Backend   │                   │  │
│  │  │  :5000      │    │   :8000     │                   │  │
│  │  └─────────────┘    └─────────────┘                   │  │
│  │         │                                             │  │
│  │  ┌──────┴──────┐                                      │  │
│  │  │   Traefik   │◄─── HTTPS (Let's Encrypt)            │  │
│  │  │   Ingress   │                                      │  │
│  │  └─────────────┘                                      │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           ▲
                           │
              GitHub Actions: build → ghcr.io → kubectl apply
```

| Component | Technology |
|-----------|------------|
| Compute | Hetzner CX22 (2 vCPU, 4GB RAM) |
| Orchestration | k3s |
| Ingress | Traefik (bundled) |
| TLS | cert-manager + Let's Encrypt |
| Registry | ghcr.io |
| IaC | Terraform (hcloud provider) |

## Prerequisites

- k3s cluster provisioned on Hetzner
- `kubectl` configured with cluster kubeconfig
- Traefik ingress controller running
- cert-manager installed with ClusterIssuer
- GitHub repository secrets configured

## Kubernetes Manifests

### Directory Structure

```
k8s/
├── base/
│   ├── kustomization.yaml
│   ├── namespace.yaml
│   ├── backend-deployment.yaml
│   ├── frontend-deployment.yaml
│   └── ingress.yaml
└── overlays/
    └── prod/
        └── kustomization.yaml
```

### Namespace

```yaml
# k8s/base/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: lightscore
```

### Backend Deployment

```yaml
# k8s/base/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: lightscore
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: ghcr.io/juusoi/light-score-backend:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: lightscore
spec:
  selector:
    app: backend
  ports:
    - port: 8000
      targetPort: 8000
```

### Frontend Deployment

```yaml
# k8s/base/frontend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: lightscore
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: ghcr.io/juusoi/light-score-frontend:latest
          ports:
            - containerPort: 5000
          env:
            - name: BACKEND_URL
              value: "http://backend.lightscore.svc.cluster.local:8000"
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /
              port: 5000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /
              port: 5000
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: lightscore
spec:
  selector:
    app: frontend
  ports:
    - port: 5000
      targetPort: 5000
```

### Ingress (Traefik)

```yaml
# k8s/base/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: lightscore
  namespace: lightscore
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
spec:
  tls:
    - hosts:
        - DOMAIN_NAME
      secretName: lightscore-tls
  rules:
    - host: DOMAIN_NAME
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 5000
```

### Kustomization

```yaml
# k8s/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: lightscore
resources:
  - namespace.yaml
  - backend-deployment.yaml
  - frontend-deployment.yaml
  - ingress.yaml
```

```yaml
# k8s/overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
images:
  - name: ghcr.io/juusoi/light-score-backend
    newTag: SHA_TAG
  - name: ghcr.io/juusoi/light-score-frontend
    newTag: SHA_TAG
```

## CI/CD Pipeline

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `KUBECONFIG_B64` | Base64-encoded kubeconfig for cluster access |

### Workflow Overview

```
push to main → CI passes → Security passes → Build images → Push to ghcr.io → kubectl apply
```

### Deploy Workflow

```yaml
# .github/workflows/deploy-hetzner.yaml
name: Deploy to Hetzner k3s

on:
  workflow_run:
    workflows: ['Security checks']
    types: [completed]
    branches: [main]
  workflow_dispatch: {}

permissions:
  contents: read
  packages: write

env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE: ghcr.io/${{ github.repository_owner }}/light-score-backend
  FRONTEND_IMAGE: ghcr.io/${{ github.repository_owner }}/light-score-frontend

jobs:
  build-push:
    name: Build and Push Images
    runs-on: ubuntu-latest
    if: github.event_name == 'workflow_dispatch' || github.event.workflow_run.conclusion == 'success'
    outputs:
      sha_tag: ${{ steps.meta.outputs.sha_tag }}
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Generate image tags
        id: meta
        run: |
          SHA_TAG="${{ github.sha }}"
          echo "sha_tag=${SHA_TAG:0:7}" >> "$GITHUB_OUTPUT"

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: .
          file: backend/Dockerfile
          push: true
          tags: |
            ${{ env.BACKEND_IMAGE }}:${{ steps.meta.outputs.sha_tag }}
            ${{ env.BACKEND_IMAGE }}:latest

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: .
          file: frontend/Dockerfile
          push: true
          tags: |
            ${{ env.FRONTEND_IMAGE }}:${{ steps.meta.outputs.sha_tag }}
            ${{ env.FRONTEND_IMAGE }}:latest

  deploy:
    name: Deploy to k3s
    runs-on: ubuntu-latest
    needs: build-push
    steps:
      - uses: actions/checkout@v4

      - name: Set up kubectl
        uses: azure/setup-kubectl@v3

      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG_B64 }}" | base64 -d > ~/.kube/config
          chmod 600 ~/.kube/config

      - name: Update image tags
        run: |
          cd k8s/overlays/prod
          sed -i "s/SHA_TAG/${{ needs.build-push.outputs.sha_tag }}/g" kustomization.yaml

      - name: Apply manifests
        run: |
          kubectl apply -k k8s/overlays/prod
          kubectl rollout status deployment/backend -n lightscore --timeout=120s
          kubectl rollout status deployment/frontend -n lightscore --timeout=120s

      - name: Verify deployment
        run: |
          kubectl get pods -n lightscore
          kubectl get ingress -n lightscore
```

## Migration Checklist

### Pre-Migration

- [ ] k3s cluster provisioned and accessible
- [ ] cert-manager installed with Let's Encrypt ClusterIssuer
- [ ] GitHub secrets configured (`KUBECONFIG_B64`)
- [ ] DNS TTL lowered (300s or less)
- [ ] Kubernetes manifests created in `k8s/`

### Deploy to Hetzner

```bash
# Manual first deployment
kubectl apply -k k8s/overlays/prod

# Verify pods running
kubectl get pods -n lightscore

# Check logs
kubectl logs -n lightscore -l app=frontend
kubectl logs -n lightscore -l app=backend

# Test via port-forward
kubectl port-forward -n lightscore svc/frontend 5000:5000
# Visit http://localhost:5000
```

### Cutover

- [ ] Verify Hetzner deployment works via port-forward
- [ ] Update DNS A record to point to Hetzner server IP
- [ ] Wait for DNS propagation (check with `dig DOMAIN_NAME`)
- [ ] Verify TLS certificate issued by cert-manager
- [ ] Run E2E tests against production URL

### Post-Migration

- [ ] Monitor for 24-48 hours
- [ ] Check application logs for errors
- [ ] Verify ESPN data refresh works
- [ ] Confirm GitHub Actions deploys successfully
- [ ] Decommission Lightsail (after validation period)

## Testing

### Smoke Tests

```bash
# Health check
curl -sf https://DOMAIN_NAME/ | head -20

# Backend API
curl -sf https://DOMAIN_NAME/api/games/weekly | jq .

# Verify internal communication
kubectl exec -n lightscore deploy/frontend -- \
  curl -sf http://backend.lightscore.svc.cluster.local:8000/
```

### E2E Tests

```bash
# Against Hetzner deployment
SERVICE_URL=https://DOMAIN_NAME make test-e2e
```

### Load Test (Optional)

```bash
# Simple load test with hey
hey -n 100 -c 10 https://DOMAIN_NAME/
```

## Operations

### Common Commands

```bash
# View pods
kubectl get pods -n lightscore

# View logs (follow)
kubectl logs -n lightscore -l app=frontend -f
kubectl logs -n lightscore -l app=backend -f

# Describe deployment
kubectl describe deployment/frontend -n lightscore

# Shell into pod
kubectl exec -it -n lightscore deploy/frontend -- /bin/sh

# Restart deployment
kubectl rollout restart deployment/frontend -n lightscore

# Scale replicas
kubectl scale deployment/frontend -n lightscore --replicas=2
```

### Certificate Status

```bash
# Check certificate
kubectl get certificate -n lightscore

# Describe for troubleshooting
kubectl describe certificate lightscore-tls -n lightscore
```

### Resource Usage

```bash
# Node resources
kubectl top nodes

# Pod resources
kubectl top pods -n lightscore
```

## Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod -n lightscore -l app=frontend
kubectl logs -n lightscore -l app=frontend --previous
```

### Image Pull Errors

Verify GHCR authentication:

```bash
kubectl get events -n lightscore --field-selector reason=Failed
```

If pulling fails, create image pull secret:

```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=USERNAME \
  --docker-password=GITHUB_PAT \
  -n lightscore
```

### TLS Certificate Not Issued

```bash
kubectl describe clusterissuer letsencrypt-prod
kubectl describe certificaterequest -n lightscore
kubectl logs -n cert-manager -l app=cert-manager
```

### Backend Not Reachable from Frontend

```bash
# Test DNS resolution
kubectl exec -n lightscore deploy/frontend -- \
  nslookup backend.lightscore.svc.cluster.local

# Test connectivity
kubectl exec -n lightscore deploy/frontend -- \
  curl -v http://backend.lightscore.svc.cluster.local:8000/
```

## Rollback

### Quick Rollback (Previous Deployment)

```bash
kubectl rollout undo deployment/frontend -n lightscore
kubectl rollout undo deployment/backend -n lightscore
```

### Rollback to Specific Revision

```bash
# View history
kubectl rollout history deployment/frontend -n lightscore

# Rollback to revision N
kubectl rollout undo deployment/frontend -n lightscore --to-revision=N
```

### Emergency: Revert to Lightsail

1. Update DNS to point back to Lightsail URL
2. Wait for DNS propagation
3. Verify Lightsail still running (if not decommissioned)

## Cost Comparison

| Item | Lightsail | Hetzner |
|------|-----------|---------|
| Compute | ~$7/mo (nano) | ~€4/mo (CX22) |
| Load Balancer | Included | ~€5/mo (optional) |
| Registry | Included | Free (ghcr.io) |
| **Total** | ~$7/mo | ~€4-9/mo |

