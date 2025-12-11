# E2E Tests CI/CD Integration

## Phase 1: Verify Tests Pass Locally

Before implementing CI changes, verify E2E tests pass against localhost:

1. Start services: `make up`
2. Install E2E dependencies: `cd e2e && bun install`
3. Install Playwright browsers: `bunx playwright install chromium --with-deps`
4. Run tests: `SERVICE_URL=http://localhost:5000 BACKEND_URL=http://localhost:8000 bun run test --project=chromium`
5. Fix any failing tests before proceeding to Phase 2

## Phase 2: CI/CD Implementation

### 1. Update CI Workflow (`ci.yaml`)

Add new `e2e` job that:
- Depends on `lint` job (same as unit tests)
- Starts backend and frontend containers using `compose.yaml`
- Waits for services to be healthy
- Installs Bun and Playwright browsers
- Runs E2E tests with `SERVICE_URL=http://localhost:5000`

```yaml
e2e:
  name: E2E Tests
  needs: [lint]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    - name: Start services
      run: docker compose up -d --build --wait
    - name: Setup Bun
      uses: oven-sh/setup-bun@v2
    - name: Install dependencies
      working-directory: ./e2e
      run: bun install && bunx playwright install chromium --with-deps
    - name: Run E2E tests
      working-directory: ./e2e
      env:
        SERVICE_URL: http://localhost:5000
        BACKEND_URL: http://localhost:8000
      run: bun run test --project=chromium
    - name: Upload test artifacts
      if: failure()
      uses: actions/upload-artifact@v4
      with:
        name: playwright-report
        path: e2e/playwright-report/
```

Update `ci-success` job to also depend on `e2e`.

### 2. Update Deploy Workflow (`deploy-lightsail.yaml`)

Add `e2e-gate` job after `deploy` that:
- Runs E2E tests against the deployed production URL
- Uses the deployed `service_url` output from deploy job

```yaml
e2e-gate:
  name: E2E Smoke Tests (Production)
  needs: [deploy]
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: oven-sh/setup-bun@v2
    - name: Install and run tests
      working-directory: ./e2e
      env:
        SERVICE_URL: ${{ needs.deploy.outputs.service_url }}
      run: |
        bun install
        bunx playwright install chromium --with-deps
        bun run test --project=chromium
```

### 3. Update E2E package.json

Update `test:ci` script to use Chromium only:

```json
"test:ci": "CI=true playwright test --project=chromium"
```

## Files to Modify

| File | Change |
|------|--------|
| `.github/workflows/ci.yaml` | Add `e2e` job, update `ci-success` dependencies |
| `.github/workflows/deploy-lightsail.yaml` | Add `e2e-gate` job after deploy |
| `e2e/package.json` | Update `test:ci` to Chromium only |

## Implementation Todos

- [ ] Start services and run E2E tests locally to verify they pass
- [ ] Fix any failing E2E tests
- [ ] Add E2E job to ci.yaml with Docker Compose, Bun, Playwright setup
- [ ] Update ci-success job to depend on e2e job
- [ ] Add e2e-gate job to deploy-lightsail.yaml
- [ ] Update test:ci script to use Chromium only
