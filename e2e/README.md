# Light Score E2E Tests

Production-ready end-to-end test suite for the Light Score NFL application using Playwright.

## Overview

This test suite provides comprehensive coverage of the Light Score application, including:

- **Frontend functionality** - User interface, navigation, responsive design
- **Backend API integration** - API endpoint testing and data validation
- **External site compatibility** - Testing against the production NFL site
- **Error handling** - Edge cases, network issues, invalid parameters
- **Accessibility** - Screen reader compatibility, keyboard navigation
- **Cross-browser testing** - Chromium, Firefox, WebKit, and mobile

## Test Structure

```
tests/
├── home.spec.ts              # Core homepage functionality
├── application.spec.ts       # Application features and navigation
├── error-handling.spec.ts    # Error states and accessibility
├── site-navigation.spec.ts   # External site health checks
├── site-interaction.spec.ts  # External site interactions
└── api/
    ├── backend.spec.ts       # Backend API endpoint testing
    └── integration.spec.ts   # Frontend-backend integration
```

## Quick Start

### Prerequisites

````bash
# Install dependencies
bun install

### Environment Variables

Playwright now requires an explicit `SERVICE_URL` pointing at the target Light Score frontend (set via GitHub secret in CI). Export the same value locally before running tests:

```bash
# Local application stack
export SERVICE_URL="http://localhost:5000"
# Optional (auto-assumed for local runs)
export BACKEND_URL="http://localhost:8000"

# Production / staging runs (frontend-only coverage)
export SERVICE_URL="https://<light-score-frontend-host>"
# Leave BACKEND_URL unset to skip backend API specs
````

> Tip: Prefix a command (`SERVICE_URL=... bun run test`) or source a local `.env` to avoid leaking the production URL into the repo.

### Unified Environment Helper

Tests now use a single helper module `tests/utils/env.ts` to resolve URLs and decide skip conditions. Import from it instead of touching `process.env` directly:

```ts
import { FRONTEND_ENV_SET, requireBackendUrl } from './utils/env';

test.skip(!FRONTEND_ENV_SET, 'SERVICE_URL not set');
await page.goto('/'); // Relies on Playwright baseURL (SERVICE_URL)

const backendUrl = requireBackendUrl(); // Throws when not running locally
const apiResponse = await request.get(`${backendUrl}/games/weekly`);
```

Helper exports:

- `FRONTEND_ENV_SET` / `BACKEND_ENV_SET` – whether env vars are explicitly set
- `requireFrontendUrl()` / `requireBackendUrl()` – fail-fast accessors with helpful messages
- `FRONTEND_URL` – normalized SERVICE_URL (empty string when unset)
- `BACKEND_URL` – `http://localhost:8000` only when local backend tests are enabled
- `frontPath(path)` / `backPath(path)` – convenience builders for absolute URLs

This avoids drift between test files, centralizes defaults, and makes it easy to adjust ports or naming in one place.

### Local vs. Production Runs

- **Local stack (`SERVICE_URL=http://localhost:5000`)**: backend API specs run automatically (they require the FastAPI service on `http://localhost:8000`).
- **Remote stack**: backend API specs are skipped because the private backend is not reachable; UI tests still exercise the production deployment.

### Code Quality

```bash
bun run lint                # Run ESLint
bun run lint:fix            # Fix auto-fixable issues

bun run type-check          # Run TypeScript type checking

bun run fmt                 # Format code with Prettier
bun run fmt:check           # Check if code is formatted

# All quality checks
bun run ci                  # Run linting and type checking
```

### Makefile Integration

From the project root, you can also use:

```bash
make lint-e2e               # E2E linting
make fmt-e2e                # E2E formatting
make ty-e2e                 # E2E type checking
make test-e2e               # E2E tests
make ci-e2e                 # All E2E quality checks
make ci                     # Full project CI (includes E2E)
```

### Running Tests

```bash
# Run all tests
bun test

# Run with UI (interactive mode)
bun run test:ui

# Run specific test suites
bun run test:local      # Local application tests only
bun run test:api        # API tests only
bun run test:external   # External site tests only
bun run test:smoke      # Quick smoke tests

# Run on specific browsers
bun run test:chromium
bun run test:firefox
bun run test:webkit
bun run test:mobile

# Debug tests
bun run test:debug
bun run test:headed

# CI/CD optimized run
bun run test:ci
```

## Test Categories

### Local Application Tests

Tests that require the Light Score application to be running locally:

- **Home Page Tests** (`home.spec.ts`) - Core UI elements and branding
- **Application Features** (`application.spec.ts`) - Navigation, games display, standings
- **Error Handling** (`error-handling.spec.ts`) - Edge cases and accessibility
- **API Integration** (`api/`) - Backend connectivity and data flow

**Setup Required:**

```bash
# Start the application stack
make up  # or equivalent docker-compose up
```

### External Site Tests

Tests that verify compatibility with the production NFL site:

- **Site Navigation** (`site-navigation.spec.ts`) - Basic site health and structure
- **Site Interaction** (`site-interaction.spec.ts`) - Link navigation and content verification

**No Local Setup Required** - These tests run against the live external site.

### API Tests

Direct testing of backend API endpoints:

- **Backend API** (`api/backend.spec.ts`) - Endpoint availability and response validation
- **Integration** (`api/integration.spec.ts`) - End-to-end data flow verification

## Configuration

### Playwright Configuration (`playwright.config.js`)

- **Multi-browser testing** - Chromium, Firefox, WebKit, Mobile Chrome
- **Retry logic** - 2 retries in CI, 0 locally
- **Timeouts** - Reasonable defaults with override options
- **Artifacts** - Screenshots, traces, and videos on failure
- **CI optimization** - GitHub Actions reporter, headless mode

### Test Patterns

Tests follow Playwright best practices:

- ✅ **Role-based locators** - `getByRole()`, `getByText()` for resilience
- ✅ **Auto-retrying assertions** - `await expect()` with built-in waits
- ✅ **Test steps** - `test.step()` for clear reporting and debugging
- ✅ **Accessibility-focused** - ARIA labels, semantic HTML testing
- ✅ **Responsive testing** - Multiple viewport sizes
- ✅ **Error boundaries** - Graceful handling of missing elements

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run E2E Tests
  run: |
    cd e2e
    bun install
    bun run install:browsers
    bun run test:ci
  env:
    SERVICE_URL: ${{ env.FRONTEND_URL }}
    BACKEND_URL: ${{ env.API_URL }}
```

### Local CI Simulation

```bash
CI=true bun run test:ci
```

## Debugging

### Test Failures

1. **View HTML Report**

   ```bash
   bun run report
   ```

2. **Debug Specific Test**

   ```bash
   bun run test:debug -- tests/home.spec.ts
   ```

3. **Run with UI Mode**
   ```bash
   bun run test:ui
   ```

### Common Issues

**"SERVICE_URL not set" - Tests Skipped**

```bash
export SERVICE_URL="http://localhost:5000"
bun test
```

**Backend Connection Failures**

```bash
# Verify backend is running
curl http://localhost:8000/games/weekly

# Set correct backend URL
export BACKEND_URL="http://localhost:8000"
```

**Browser Installation Issues**

```bash
bun run install:browsers
# On Linux/CI:
bun run install:deps
```

## Test Data and Expectations

### Expected Application Behavior

- **Games Display** - Live games, scheduled games, final scores
- **Standings** - Division-organized team records (W-L-T format)
- **Navigation** - Previous/next week functionality with URL parameters
- **Responsive Design** - Functional across desktop, tablet, mobile viewports
- **Accessibility** - Proper ARIA labels, keyboard navigation, screen reader support

### Fallback Handling

Tests verify graceful degradation when:

- Backend APIs are unavailable
- Data is missing or malformed
- Network requests timeout
- Invalid URL parameters are provided

## Maintenance

### Adding New Tests

1. **Follow naming convention** - `feature.spec.ts`
2. **Use test.describe()** for grouping
3. **Include test.step()** for clarity
4. **Add appropriate skips** for environment dependencies
5. **Update package.json scripts** if needed

### Updating Dependencies

```bash
bun update @playwright/test
bun run install:browsers  # Update browsers after Playwright updates
```

### Performance Monitoring

Tests include response time verification and artifact collection for performance analysis.

## Architecture Integration

This e2e test suite integrates with the Light Score architecture:

- **Frontend (Flask)** - UI and user experience testing
- **Backend (FastAPI)** - API endpoint and data validation
- **Functions** - Indirect testing via cached data validation
- **External APIs** - ESPN integration health checks

For more details, see the project's main documentation and architecture guides.
