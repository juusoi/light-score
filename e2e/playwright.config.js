// Playwright config for Light Score e2e
import { defineConfig, devices } from '@playwright/test';

const LOCAL_FRONTEND_URL = 'http://localhost:5000';
const LOCAL_BACKEND_URL = 'http://localhost:8000';

function normalizeUrl(url) {
  if (!url) return '';
  const trimmed = url.trim();
  if (!trimmed) return '';
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
}

// SERVICE_URL defaults to local development environment if not set
const FRONTEND_URL = normalizeUrl(
  process.env.SERVICE_URL || LOCAL_FRONTEND_URL,
);
if (!FRONTEND_URL) {
  throw new Error(
    '[e2e] Unable to determine frontend URL. Check SERVICE_URL environment variable.',
  );
}
const FRONTEND_ENV_SET = true;
const isLocalFrontend = FRONTEND_URL === LOCAL_FRONTEND_URL;

// Backend API tests run only when pointing at the local FastAPI instance.
const normalizedBackend = normalizeUrl(process.env.BACKEND_URL || '');
const backendExplicitLocal = normalizedBackend === LOCAL_BACKEND_URL;
const backendImplicitLocal = isLocalFrontend && !normalizedBackend;
const BACKEND_ENV_SET = backendExplicitLocal || backendImplicitLocal;
const BACKEND_URL = BACKEND_ENV_SET ? LOCAL_BACKEND_URL : '';

if (!BACKEND_ENV_SET) {
  console.warn(
    `[e2e] BACKEND_URL not set to ${LOCAL_BACKEND_URL} – backend API tests will be skipped (production runs rely on frontend only).`,
  );
}

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  expect: {
    timeout: 5_000,
    // Use auto-retrying web-first assertions
    toMatchSnapshot: { maxDiffPixels: 100 },
  },
  // Global test setup
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Reporters for different environments
  reporter: process.env.CI
    ? [
      ['github'],
      ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ]
    : [['list'], ['html', { outputFolder: 'playwright-report' }]],

  use: {
    headless: true,
    viewport: { width: 1280, height: 720 },
    actionTimeout: 10_000,
    navigationTimeout: 30_000,

    // Resolve relative URLs against unified frontend URL
    baseURL: FRONTEND_URL,

    // Screenshots and traces for debugging
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
  },

  // Test projects for different browsers and scenarios
  projects: [
    // Use 'chromium' for CI (bundled browser), 'chrome' for local (system Chrome)
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // Mobile testing
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'], channel: 'chrome' },
    },
    // API testing
    {
      name: 'api',
      testMatch: '**/api/*.spec.ts',
      use: {
        // API tests don't need a browser
      },
    },
  ],

  // Global test patterns
  testMatch: '**/*.spec.ts',
  testIgnore: '**/node_modules/**',
  // Expose resolved URLs for test diagnostics (accessible via test.info().project.metadata)
  metadata: {
    frontendUrl: FRONTEND_URL,
    backendUrl: BACKEND_URL,
    frontendEnvSet: FRONTEND_ENV_SET,
    backendEnvSet: BACKEND_ENV_SET,
  },
});
