// Unified environment URL helper for e2e tests.
// Centralizes resolution of frontend (Flask) and backend (FastAPI) service URLs.
// Tests should import from this module instead of accessing process.env directly.

const LOCAL_FRONTEND_URL = 'http://localhost:5000';
const LOCAL_BACKEND_URL = 'http://localhost:8000';

function normalize(value: string | undefined): string {
  if (!value) return '';
  const trimmed = value.trim();
  if (trimmed.length === 0) return '';
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
}

const normalizedFrontendUrl = normalize(process.env.SERVICE_URL);
const normalizedBackendEnv = normalize(process.env.BACKEND_URL);
const isLocalFrontend = normalizedFrontendUrl === LOCAL_FRONTEND_URL;

// Raw environment presence flags (whether user explicitly set them)
export const FRONTEND_ENV_SET = normalizedFrontendUrl.length > 0;

const resolvedBackendUrl =
  normalizedBackendEnv.length > 0
    ? normalizedBackendEnv
    : isLocalFrontend
      ? LOCAL_BACKEND_URL
      : '';

// Backend tests only run when targeting the local FastAPI service
export const BACKEND_ENV_SET =
  isLocalFrontend && resolvedBackendUrl === LOCAL_BACKEND_URL;

// Resolved URLs (empty string when unavailable)
export const FRONTEND_URL = normalizedFrontendUrl;
export const BACKEND_URL = BACKEND_ENV_SET ? LOCAL_BACKEND_URL : '';

// Convenience predicates for skipping tests that require explicit configuration
export const REQUIRE_FRONTEND = () => FRONTEND_ENV_SET;
export const REQUIRE_BACKEND = () => BACKEND_ENV_SET;

export function requireFrontendUrl(): string {
  if (!FRONTEND_ENV_SET) {
    throw new Error(
      '[e2e] SERVICE_URL is not defined. Export SERVICE_URL (e.g., http://localhost:5000 or production endpoint) before running these tests.',
    );
  }
  return normalize(FRONTEND_URL);
}

export function requireBackendUrl(): string {
  if (!BACKEND_ENV_SET) {
    throw new Error(
      `[e2e] Backend API tests require SERVICE_URL=${LOCAL_FRONTEND_URL} (local Flask UI) and BACKEND_URL=${LOCAL_BACKEND_URL}. Skip backend tests when targeting production.`,
    );
  }
  return LOCAL_BACKEND_URL;
}

// Helper to build full paths against the frontend baseURL
export function frontPath(path: string): string {
  const base = requireFrontendUrl();
  if (!path.startsWith('/')) {
    return `${base}/${path}`;
  }
  return `${base}${path}`;
}

// Helper to build full paths against the backend baseURL
export function backPath(path: string): string {
  const base = requireBackendUrl();
  if (!path.startsWith('/')) {
    return `${base}/${path}`;
  }
  return `${base}${path}`;
}
