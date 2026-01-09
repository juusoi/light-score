import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET } from '../utils/env';

test.describe('Light Score - Frontend-Backend Integration', () => {
  test.skip(
    !FRONTEND_ENV_SET,
    'SERVICE_URL not configured - skipping frontend-backend integration tests',
  );

  test.beforeEach(async ({ page }) => {
    // Force seasonType=2 to ensure consistent testable state (Standings)
    await page.goto('/?seasonType=2', { waitUntil: 'networkidle' });
  });

  test('frontend successfully fetches and displays backend data', async ({
    page,
  }) => {
    await test.step('verify data is loaded from backend', async () => {
      // Check if any of the main content sections have data
      // This indicates successful backend communication

      const liveSection = page.locator('.ttx-panel:has(h2:text("Live"))');
      const gamesSection = page.locator('.ttx-panel:has(h2:text("Games"))');
      const standingsSection = page.locator(
        '.ttx-panel:has(h2:text("Standings"))',
      );

      // At least one section should show either data or "No X available" message
      const hasLiveContent =
        (await liveSection.locator('.ttx-item').count()) > 0;
      const hasGamesContent =
        (await gamesSection.locator('.ttx-item').count()) > 0;
      const hasStandingsContent =
        (await standingsSection.locator('.ttx-item').count()) > 0;

      const hasNoLiveMessage =
        (await liveSection.getByText('No live games').count()) > 0;
      const hasNoGamesMessage =
        (await gamesSection.getByText('No games').count()) > 0;
      const hasNoStandingsMessage =
        (await standingsSection.getByText('No standings available').count()) >
        0;

      // Either we have content or appropriate "no content" messages
      const hasValidState =
        (hasLiveContent || hasNoLiveMessage) &&
        (hasGamesContent || hasNoGamesMessage) &&
        (hasStandingsContent || hasNoStandingsMessage);

      expect(hasValidState).toBeTruthy();
    });

    await test.step('verify season context is displayed', async () => {
      // Season information should be present, indicating backend context API worked
      const seasonLine = page.locator('.ttx-season-line');
      await expect(seasonLine).toBeVisible();

      // Should show year and season type
      await expect(seasonLine).toContainText(/20\d{2}/);
    });

    await test.step('verify navigation parameters work', async () => {
      // Navigation links should have proper URLs with parameters
      const prevLink = page.getByRole('link', { name: /prev/i });
      const nextLink = page.getByRole('link', { name: /next/i });

      await expect(prevLink).toHaveAttribute('href', /[?&]year=/);
      await expect(prevLink).toHaveAttribute('href', /[?&]week=/);
      await expect(prevLink).toHaveAttribute('href', /[?&]seasonType=/);

      await expect(nextLink).toHaveAttribute('href', /[?&]year=/);
      await expect(nextLink).toHaveAttribute('href', /[?&]week=/);
      await expect(nextLink).toHaveAttribute('href', /[?&]seasonType=/);
    });
  });

  test('frontend gracefully handles backend unavailability', async ({
    page,
  }) => {
    await test.step('test with potentially unavailable backend', async () => {
      // This test checks what happens when backend is down
      // We can't easily simulate this, but we can check error page handling

      // First, try to navigate to a page that might cause backend errors
      await page.goto('/?year=1900&week=999&seasonType=invalid', {
        waitUntil: 'networkidle',
        timeout: 15000,
      });

      // Page should still load, even if with errors or no data
      await expect(page.getByText('Light Score')).toBeVisible();

      // Should either show data or appropriate error/no-data messages
      const pageText = await page.textContent('body');
      expect(pageText?.length).toBeGreaterThan(50);
    });
  });

  test('navigation between weeks maintains data consistency', async ({
    page,
  }) => {
    await page.goto('/?seasonType=2', { waitUntil: 'networkidle' });

    let initialState: { weekText: string | null; url: string };

    await test.step('capture initial state', async () => {
      // Get initial week information
      const initialWeekText = await page
        .locator('.ttx-week-label')
        .textContent();
      const initialUrl = page.url();

      expect(initialWeekText).toMatch(/week \d+/i);

      // Store for comparison
      initialState = { weekText: initialWeekText, url: initialUrl };
    });

    await test.step('navigate to previous week', async () => {
      const prevLink = page.getByRole('link', { name: /prev/i });
      await prevLink.click();
      await page.waitForLoadState('networkidle');

      // Verify navigation occurred
      const newUrl = page.url();
      expect(newUrl).not.toBe(initialState.url);

      // Page should still be functional
      await expect(page.getByText('Light Score')).toBeVisible();

      // Week label should have changed (or stayed same if at boundary)
      const newWeekText = await page.locator('.ttx-week-label').textContent();
      expect(newWeekText).toMatch(/week \d+/i);
    });

    await test.step('navigate to next week', async () => {
      const nextLink = page.getByRole('link', { name: /next/i });
      await nextLink.click();
      await page.waitForLoadState('networkidle');

      // Page should still be functional
      await expect(page.getByText('Light Score')).toBeVisible();

      // Week label should be present
      const finalWeekText = await page.locator('.ttx-week-label').textContent();
      expect(finalWeekText).toMatch(/week \d+/i);
    });
  });

  test('data formatting and Finnish timezone display works correctly', async ({
    page,
  }) => {
    await page.goto('/?seasonType=2', { waitUntil: 'networkidle' });

    await test.step('verify game time formatting', async () => {
      const upcomingGames = page.locator('.ttx-status-upcoming');
      const upcomingCount = await upcomingGames.count();

      if (upcomingCount > 0) {
        const firstUpcomingTime = await upcomingGames.first().textContent();

        // Should have some time information (Finnish format expected)
        expect(firstUpcomingTime?.trim().length).toBeGreaterThan(0);

        // Common Finnish time formats might include dots or colons
        const hasTimeFormat = /\d{1,2}[:.]\d{2}|\d{1,2}\.\d{1,2}/.test(
          firstUpcomingTime || '',
        );

        // If not a recognizable time format, should at least say "scheduled" or similar
        const hasScheduledText = /scheduled|tulossa|upcoming/i.test(
          firstUpcomingTime || '',
        );

        expect(hasTimeFormat || hasScheduledText).toBeTruthy();
      }
    });

    await test.step('verify standings data integrity', async () => {
      const records = page.locator('.ttx-record');
      const recordCount = await records.count();

      if (recordCount > 0) {
        // Check first few records for proper format
        for (let i = 0; i < Math.min(recordCount, 3); i++) {
          const record = records.nth(i);
          const recordText = await record.textContent();

          // Clean whitespace and check for W-L or W-L-T format
          const cleanedText = recordText
            ?.replace(/\s+/g, '')
            .replace(/[·]/g, '');
          expect(cleanedText).toMatch(/^\d+-\d+(-\d+)?$/);

          // Individual components should be visible
          await expect(record.locator('.ttx-record-wins')).toBeVisible();
          await expect(record.locator('.ttx-record-losses')).toBeVisible();
        }
      }
    });
  });

  test('responsive design works with real backend data', async ({ page }) => {
    const viewports = [
      { width: 375, height: 667, name: 'mobile' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 1920, height: 1080, name: 'desktop' },
    ];

    for (const viewport of viewports) {
      await test.step(`test ${viewport.name} layout with backend data`, async () => {
        await page.setViewportSize(viewport);
        await page.goto('/?seasonType=2', { waitUntil: 'networkidle' });

        // Core functionality should work at all viewport sizes
        await expect(page.getByText('Light Score')).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Live' })).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Games' }),
        ).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Standings' }),
        ).toBeVisible();

        // Navigation should be accessible
        await expect(page.getByRole('link', { name: /prev/i })).toBeVisible();
        await expect(page.getByRole('link', { name: /next/i })).toBeVisible();

        // Content should not overflow
        const container = page.locator('.ttx-container');
        const containerBox = await container.boundingBox();

        if (containerBox) {
          expect(containerBox.width).toBeLessThanOrEqual(viewport.width + 50); // Small tolerance for scrollbar
        }
      });
    }
  });
});
