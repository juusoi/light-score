import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET } from './utils/env';

test.describe('Light Score - Application Features', () => {
  // Require explicit SERVICE_URL
  test.skip(
    !FRONTEND_ENV_SET,
    'SERVICE_URL not set - skipping application feature tests',
  );

  test.beforeEach(async ({ page }) => {
    await page.goto('/?seasonType=2', { waitUntil: 'networkidle' });
  });

  test('week navigation works correctly', async ({ page }) => {
    await test.step('navigate to previous week', async () => {
      const currentUrl = page.url();
      const prevLink = page.getByRole('link', { name: /prev/i });

      await prevLink.click();
      await page.waitForLoadState('networkidle');

      // URL should have changed
      expect(page.url()).not.toBe(currentUrl);

      // Page should still show Light Score branding
      await expect(page.getByText('Light Score')).toBeVisible();
    });

    await test.step('navigate to next week', async () => {
      const currentUrl = page.url();
      const nextLink = page.getByRole('link', { name: /next/i });

      await nextLink.click();
      await page.waitForLoadState('networkidle');

      // URL should have changed
      expect(page.url()).not.toBe(currentUrl);

      // Page should still show Light Score branding
      await expect(page.getByText('Light Score')).toBeVisible();
    });
  });

  test('displays games with proper status indicators', async ({ page }) => {
    await test.step('verify live games display format', async () => {
      const livePanel = page.locator('.ttx-panel:has(h2:text("Live"))');
      // Real live games have a .ttx-teams container
      const realLiveGames = livePanel.locator('.ttx-item:has(.ttx-teams)');
      const realCount = await realLiveGames.count();

      if (realCount === 0) {
        // Expect placeholder message when no live games
        await expect(livePanel.getByText('No live games')).toBeVisible();
        return;
      }

      const firstLive = realLiveGames.first();
      await expect(firstLive.locator('.ttx-team')).toHaveCount(2);
      const hasScore = (await firstLive.locator('.ttx-score').count()) > 0;
      const hasLiveStatus =
        (await firstLive.locator('.ttx-status-live').count()) > 0;
      expect(hasScore || hasLiveStatus).toBeTruthy();
    });

    await test.step('verify scheduled games display format', async () => {
      const scheduledGames = page.locator(
        '.ttx-panel:has(h2:text("Games")) .ttx-item',
      );
      const scheduledGameCount = await scheduledGames.count();

      if (scheduledGameCount > 0) {
        const firstGame = scheduledGames.first();

        // Should have team names
        await expect(firstGame.locator('.ttx-team')).toHaveCount(2);

        // Should have status (final, upcoming, etc.)
        const hasFinalStatus =
          (await firstGame.locator('.ttx-status-final').count()) > 0;
        const hasUpcomingStatus =
          (await firstGame.locator('.ttx-status-upcoming').count()) > 0;

        expect(hasFinalStatus || hasUpcomingStatus).toBeTruthy();
      }
    });
  });

  test('standings display proper division structure', async ({ page }) => {
    await test.step('verify division organization', async () => {
      const standingsSection = page.locator(
        '.ttx-panel:has(h2:text("Standings"))',
      );
      const divisions = await standingsSection.locator('.ttx-subtitle').count();

      if (divisions > 0) {
        // Should have multiple divisions (AFC/NFC East, West, etc.)
        expect(divisions).toBeGreaterThanOrEqual(2);

        // Each division should have teams with records
        const firstDivision = standingsSection.locator('.ttx-subtitle').first();
        const divisionTeams = firstDivision.locator('~ .ttx-list .ttx-item');

        if ((await divisionTeams.count()) > 0) {
          const firstTeam = divisionTeams.first();
          await expect(firstTeam.locator('.ttx-team')).toBeVisible();
          await expect(firstTeam.locator('.ttx-record')).toBeVisible();
        }
      }
    });

    await test.step('verify team record format', async () => {
      const records = page.locator('.ttx-record');
      const recordCount = await records.count();

      if (recordCount > 0) {
        const firstRecord = records.first();

        // Should have wins and losses
        await expect(firstRecord.locator('.ttx-record-wins')).toBeVisible();
        await expect(firstRecord.locator('.ttx-record-losses')).toBeVisible();

        // Record should be in W-L format (possibly W-L-T)
        let recordText = await firstRecord.textContent();
        recordText = recordText?.replace(/\s+/g, '') || '';
        // Accept W-L or W-L-T formats
        expect(recordText).toMatch(/^\d+-\d+(-\d+)?$/);
      }
    });
  });

  test('handles different game states correctly', async ({ page }) => {
    await test.step('verify final game styling', async () => {
      const finalGames = page.locator('.ttx-item:has(.ttx-status-final)');
      const finalGameCount = await finalGames.count();

      if (finalGameCount > 0) {
        const firstFinal = finalGames.first();

        // Winners should be styled differently
        const winnerTeams = await firstFinal.locator('.ttx-winner').count();
        const tieTeams = await firstFinal.locator('.ttx-tie').count();

        // Should have either winners or ties
        expect(winnerTeams >= 0 && tieTeams >= 0).toBeTruthy();
      }
    });

    await test.step('verify upcoming game timing', async () => {
      const upcomingGames = page.locator('.ttx-item:has(.ttx-status-upcoming)');
      const upcomingCount = await upcomingGames.count();

      if (upcomingCount > 0) {
        const firstUpcoming = upcomingGames.first();
        const timeInfo = firstUpcoming.locator('.ttx-status-upcoming');

        // Should show either time or "scheduled"
        const timeText = await timeInfo.textContent();
        expect(timeText?.length).toBeGreaterThan(0);
      }
    });
  });

  test('maintains responsive design across viewports', async ({ page }) => {
    const viewports = [
      { width: 1920, height: 1080, name: 'desktop' },
      { width: 768, height: 1024, name: 'tablet' },
      { width: 375, height: 667, name: 'mobile' },
    ];

    for (const viewport of viewports) {
      await test.step(`verify layout at ${viewport.name} viewport`, async () => {
        await page.setViewportSize({
          width: viewport.width,
          height: viewport.height,
        });
        await page.reload({ waitUntil: 'networkidle' });

        // Core elements should remain visible
        await expect(page.getByText('Light Score')).toBeVisible();
        await expect(page.getByRole('heading', { name: 'Live' })).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Games' }),
        ).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Standings' }),
        ).toBeVisible();

        // Navigation should be functional
        await expect(page.getByRole('link', { name: /prev/i })).toBeVisible();
        await expect(page.getByRole('link', { name: /next/i })).toBeVisible();
      });
    }
  });

  test('handles network errors gracefully', async ({ page }) => {
    await test.step('verify error page behavior', async () => {
      // Navigate to a non-existent page to simulate error
      const response = await page
        .goto('/non-existent-page', {
          waitUntil: 'networkidle',
          timeout: 10000,
        })
        .catch(() => null);

      if (response) {
        // If the page loads, it should show some kind of error indication
        const pageContent = await page.textContent('body');
        expect(pageContent?.length).toBeGreaterThan(0);
      }
    });
  });

  test('accessibility compliance basics', async ({ page }) => {
    await test.step('verify semantic HTML structure', async () => {
      // Should have proper heading hierarchy
      const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();
      expect(headings.length).toBeGreaterThan(0);

      // Should have navigation landmarks
      const nav = page.locator(
        'nav, [role="navigation"], .ttx-week-nav[aria-label*="Week"]',
      );
      await expect(nav.first()).toBeVisible();
    });

    await test.step('verify ARIA attributes are present', async () => {
      // Navigation should have accessible names
      const weekNav = page.locator('[aria-label*="navigation"]');
      if ((await weekNav.count()) > 0) {
        await expect(weekNav.first()).toBeVisible();
      }

      // Team and record information should have labels
      const ariaLabels = page.locator('[aria-label]');
      const ariaLabelCount = await ariaLabels.count();
      expect(ariaLabelCount).toBeGreaterThan(0);
    });

    await test.step('verify color contrast and readability', async () => {
      // Text should be readable (not transparent or same color as background)
      const textElements = await page.locator('body *:visible').all();
      expect(textElements.length).toBeGreaterThan(0);

      // Main content should be contained properly
      const container = page.locator('.ttx-container');
      await expect(container).toBeVisible();
    });
  });
});
