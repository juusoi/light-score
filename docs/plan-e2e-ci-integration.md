# E2E Tests CI/CD Integration

## Overview

E2E tests are integrated into the CI/CD pipeline at three stages:

1. **Mock Tests (CI)** - Deterministic tests against fixture data
2. **Integration Tests (CI)** - Full tests against live localhost services
3. **Smoke Tests (Post-Deploy)** - Critical path verification against production

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Lint     │────▶│   E2E Mock  │────▶│  E2E Local  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                       │
       ▼                                       ▼
┌─────────────┐                         ┌─────────────┐
│ Unit Tests  │────────────────────────▶│  ci-success │
└─────────────┘                         └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Deploy    │
                                        └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │ E2E Smoke   │
                                        └─────────────┘
```

## CI Pipeline Jobs

### E2E Mock Tests (`e2e-mock`)

Runs against Docker Compose with `MOCK_ESPN=true` for predictable fixture data.

- **Depends on**: `lint`
- **Runs in parallel with**: `tests`
- **Purpose**: Verify business logic with deterministic data

```bash
# Local equivalent
MOCK_ESPN=true make up
MOCK_ESPN=true SERVICE_URL=http://localhost:5000 BACKEND_URL=http://localhost:8000 make test-e2e
```

### E2E Integration Tests (`e2e-local`)

Full test suite against localhost services with live ESPN data simulation.

- **Depends on**: `lint`, `tests`, `e2e-mock`
- **Purpose**: Final pre-deploy gate ensuring full integration works

```bash
# Local equivalent
make up
SERVICE_URL=http://localhost:5000 BACKEND_URL=http://localhost:8000 make test-e2e
```

### E2E Smoke Tests (`e2e-smoke`)

Lightweight critical path tests against production after deployment.

- **Depends on**: `deploy`
- **Environment**: `production`
- **Purpose**: Verify deployment succeeded and critical paths work

```bash
# Local equivalent (against production)
SERVICE_URL=https://your-production-url.com bun run test:smoke
```

## Test Organization

### Smoke Tests (`@smoke` tag)

Tag critical tests with `@smoke` in the test name for post-deploy verification:

```typescript
test('displays core page structure and branding @smoke', async ({ page }) => {
  // Critical path test
});
```

Run smoke tests:
```bash
bun run test:smoke
```

### Mock Tests (`e2e/tests/mock/`)

Tests that require `MOCK_ESPN=true` for fixture data:

```typescript
test.skip(!MOCK_MODE, 'MOCK_ESPN not set - skipping mock fixture tests');
```

## npm Scripts

| Script | Description |
|--------|-------------|
| `test` | Run all tests |
| `test:ci` | CI mode (Chromium + Firefox) |
| `test:smoke` | Smoke tests only (`@smoke` tagged) |
| `test:chromium` | Chromium only |

## GitHub Configuration

### Required Secrets

| Secret | Scope | Description |
|--------|-------|-------------|
| `AWS_ROLE_TO_ASSUME` | Repository | AWS OIDC role for deployment |
| `LIGHTSCORE_DOMAIN` | Repository | Custom domain (optional) |
| `PRODUCTION_URL` | `production` environment | Production URL for smoke tests |

### Environment Setup

1. Go to **Settings > Environments**
2. Create `production` environment
3. Add `PRODUCTION_URL` secret (e.g., `https://lightscore-prod.xxx.amazonaws.com`)
4. Optionally add protection rules (required reviewers, wait timer)

## Local Development

### Run all E2E tests locally

```bash
# Start services
make up

# Run tests
make test-e2e
```

### Run mock tests locally

```bash
# Start services in mock mode
make mock-up

# Run all tests (mock tests will execute)
MOCK_ESPN=true make test-e2e
```

### Run smoke tests locally

```bash
# Against local
SERVICE_URL=http://localhost:5000 bun run test:smoke

# Against production
SERVICE_URL=https://your-prod-url.com bun run test:smoke
```

## Files Modified

| File | Changes |
|------|---------|
| `.github/workflows/ci.yaml` | Added `e2e-mock` and `e2e-local` jobs |
| `.github/workflows/deploy-lightsail.yaml` | Added `e2e-smoke` job |
| `e2e/package.json` | Added `test:smoke` script |
| `e2e/tests/home.spec.ts` | Added `@smoke` tags |
| `e2e/tests/site-navigation.spec.ts` | Added `@smoke` tag |
