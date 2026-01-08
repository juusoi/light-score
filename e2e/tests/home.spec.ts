import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET } from './utils/env';

test.describe('Light Score - Home Page', () => {
  // Require explicit SERVICE_URL for UI tests to avoid accidental hits when app not running
  test.skip(!FRONTEND_ENV_SET, 'SERVICE_URL not set - skipping local UI tests');

  test.beforeEach(async ({ page }) => {
    // Navigate to home page before each test
    // Force seasonType=2 to ensure Standings are visible for these tests
    await page.goto('/?seasonType=2', { waitUntil: 'networkidle' });
  });

  test.describe('@smoke', () => {
    test('displays core page structure and branding', async ({ page }) => {
      await test.step('verify page title and brand', async () => {
        await expect(page).toHaveTitle(/Light Score/);
        await expect(page.getByText('Light Score')).toBeVisible();
      });

      await test.step('verify main content areas are present', async () => {
        // Check for main sections using semantic roles and text
        await expect(page.getByRole('heading', { name: 'Live' })).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Games' }),
        ).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Standings' }),
        ).toBeVisible();
      });

      await test.step('verify teletext styling is applied', async () => {
        const container = page.locator('.ttx-container');
        await expect(container).toBeVisible();
        await expect(container).toHaveCSS('font-family', /monospace/);
      });
    });

    test('shows week navigation controls', async ({ page }) => {
      await test.step('verify navigation elements are present', async () => {
        // Look for the navigation element by aria-label instead of role
        const weekNav = page.locator('[aria-label*="Week navigation"]');
        await expect(weekNav).toBeVisible();

        await expect(page.getByRole('link', { name: /prev/i })).toBeVisible();
        await expect(page.getByRole('link', { name: /next/i })).toBeVisible();
        await expect(page.getByText(/week \d+/i)).toBeVisible();
      });

      await test.step('verify navigation links are functional', async () => {
        const prevLink = page.getByRole('link', { name: /prev/i });
        const nextLink = page.getByRole('link', { name: /next/i });

        // Links should have valid href attributes
        await expect(prevLink).toHaveAttribute('href', /\?/);
        await expect(nextLink).toHaveAttribute('href', /\?/);
      });
    });
  });

  test('displays season and year information', async ({ page }) => {
    await test.step('verify season context is shown', async () => {
      // Season type should be displayed
      const seasonInfo = page.locator('.ttx-season-line');
      await expect(seasonInfo).toBeVisible();

      // Should show current year
      await expect(seasonInfo).toContainText(/20\d{2}/);
    });
  });

  test('handles games data display appropriately', async ({ page }) => {
    await test.step('verify live games section', async () => {
      const liveSection = page
        .getByRole('heading', { name: 'Live' })
        .locator('..')
        .locator('..');
      await expect(liveSection).toBeVisible();

      // Should show either games or "No live games" message
      const hasLiveGames =
        (await liveSection.locator('.ttx-teams').count()) > 0;
      const hasNoGamesMessage =
        (await liveSection.getByText('No live games').count()) > 0;

      expect(hasLiveGames || hasNoGamesMessage).toBeTruthy();
    });

    await test.step('verify scheduled games section', async () => {
      const gamesSection = page
        .getByRole('heading', { name: 'Games' })
        .locator('..')
        .locator('..');
      await expect(gamesSection).toBeVisible();

      // Should show either games or "No games" message
      const hasGames = (await gamesSection.locator('.ttx-teams').count()) > 0;
      const hasNoGamesMessage =
        (await gamesSection.getByText('No games').count()) > 0;

      expect(hasGames || hasNoGamesMessage).toBeTruthy();
    });
  });

  test('displays standings information', async ({ page }) => {
    await test.step('verify standings section structure', async () => {
      const standingsSection = page
        .getByRole('heading', { name: 'Standings' })
        .locator('..')
        .locator('..');
      await expect(standingsSection).toBeVisible();

      // Should show either division standings or "No standings available" message
      const hasDivisions =
        (await standingsSection.locator('.ttx-subtitle').count()) > 0;
      const hasNoStandings =
        (await standingsSection.getByText('No standings available').count()) >
        0;

      expect(hasDivisions || hasNoStandings).toBeTruthy();
    });

    await test.step('verify team records format when present', async () => {
      const recordElements = await page.locator('.ttx-record').count();

      if (recordElements > 0) {
        // If standings are present, verify they have proper win-loss format
        const firstRecord = page.locator('.ttx-record').first();
        await expect(firstRecord).toBeVisible();

        // Check that individual record components are present
        await expect(firstRecord.locator('.ttx-record-wins')).toBeVisible();
        await expect(firstRecord.locator('.ttx-record-losses')).toBeVisible();
      }
    });
  });

  test('is responsive and accessible', async ({ page }) => {
    await test.step('verify accessibility structure', async () => {
      // Check for proper heading hierarchy
      const h1Count = await page.locator('h1').count();
      const h2Count = await page.locator('h2').count();

      expect(h2Count).toBeGreaterThanOrEqual(3); // Live, Games, Standings

      // Verify ARIA labels are present
      await expect(page.locator('[aria-label*="Teams"]').first()).toBeVisible();
      await expect(
        page.locator('[aria-label*="Record"]').first(),
      ).toBeVisible();
    });

    await test.step('test mobile viewport', async () => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.reload();

      // Core elements should still be visible on mobile
      await expect(page.getByText('Light Score')).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Live' })).toBeVisible();
    });
  });
});
