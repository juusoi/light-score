---
description: 'Playwright test generation instructions for Light Score E2E tests'
applyTo: 'e2e/**'
---

## Test Writing Guidelines

### Code Quality Standards

- **Locators**: Prioritize user-facing, role-based locators (`getByRole`, `getByLabel`, `getByText`, etc.) for resilience and accessibility. Use `test.step()` to group interactions and improve test readability and reporting.
- **Assertions**: Use auto-retrying web-first assertions. These assertions start with the `await` keyword (e.g., `await expect(locator).toHaveText()`). Avoid `expect(locator).toBeVisible()` unless specifically testing for visibility changes.
- **Timeouts**: Rely on Playwright's built-in auto-waiting mechanisms. Avoid hard-coded waits or increased default timeouts.
- **Clarity**: Use descriptive test and step titles that clearly state the intent. Add comments only to explain complex logic or non-obvious interactions.

### Test Structure

- **Imports**: Start with `import { test, expect } from '@playwright/test';`.
- **Organization**: Group related tests for a feature under a `test.describe()` block.
- **Hooks**: Use `beforeEach` for setup actions common to all tests in a `describe` block (e.g., navigating to a page).
- **Titles**: Follow a clear naming convention, such as `Feature - Specific action or scenario`.

### File Organization

- **Location**: Store all test files in the `e2e/tests/` directory.
- **Naming**: Use the convention `<feature-or-page>.spec.ts` (e.g., `home.spec.ts`, `site-navigation.spec.ts`).
- **API Tests**: Place backend API tests in `e2e/tests/api/` (e.g., `backend.spec.ts`, `integration.spec.ts`).
- **Utilities**: Shared helpers and utilities go in `e2e/tests/utils/` (e.g., `env.ts`).
- **Scope**: Aim for one test file per major application feature or page.

### Assertion Best Practices

- **UI Structure**: Use `toMatchAriaSnapshot` to verify the accessibility tree structure of a component. This provides a comprehensive and accessible snapshot.
- **Element Counts**: Use `toHaveCount` to assert the number of elements found by a locator.
- **Text Content**: Use `toHaveText` for exact text matches and `toContainText` for partial matches.
- **Navigation**: Use `toHaveURL` to verify the page URL after an action.

## Example Test Structure

```typescript
import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application before each test
    // baseURL is configured in playwright.config.js (defaults to localhost:5000)
    await page.goto('/');
  });

  test('displays NFL scoreboard heading', async ({ page }) => {
    await test.step('Verify page title and heading', async () => {
      await expect(page).toHaveTitle(/Light Score/);
      await expect(page.getByRole('heading', { level: 1 })).toContainText('NFL');
    });
  });

  test('shows navigation links', async ({ page }) => {
    await test.step('Verify navigation is present', async () => {
      const nav = page.getByRole('navigation');
      await expect(nav).toBeVisible();
      await expect(nav.getByRole('link')).toHaveCount.greaterThan(0);
    });
  });
});
```

## Environment Configuration

- Tests use `SERVICE_URL` env var for frontend (defaults to `http://localhost:5000`).
- Backend API tests use `BACKEND_URL` env var (defaults to `http://localhost:8000`).
- Run `make up` before executing E2E tests to start local services.

## Test Execution Strategy

1. **Start services**: Run `make up` to start backend and frontend containers
2. **Initial Run**: Execute tests with `make test-e2e` or `cd e2e && bun run test`
3. **Single browser**: Run `cd e2e && bunx playwright test --project=chromium` for faster iteration
4. **Debug Failures**: Use `bunx playwright test --debug` or check `e2e/playwright-report/`
5. **Iterate**: Refine locators, assertions, or test logic as needed
6. **Validate**: Ensure tests pass consistently before pushing

## Quality Checklist

Before finalizing tests, ensure:

- [ ] All locators are accessible and specific and avoid strict mode violations
- [ ] Tests are grouped logically and follow a clear structure
- [ ] Assertions are meaningful and reflect user expectations
- [ ] Tests follow consistent naming conventions
- [ ] Code is properly formatted (`make fmt-e2e`) and passes linting (`make lint-e2e`)
