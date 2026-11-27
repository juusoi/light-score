import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET } from './utils/env';

const MOCK_MODE =
  process.env.MOCK_ESPN === 'true' || process.env.MOCK_ESPN === '1';

test.describe('Light Score - No Scores (Spoiler-Free Upcoming Games)', () => {
  test.skip(!FRONTEND_ENV_SET, 'SERVICE_URL not set - skipping local UI tests');

  test.describe('@smoke', () => {
    test('renders spoiler-free upcoming games view without results or nav', async ({
      page,
    }) => {
      await page.goto('/no-scores', { waitUntil: 'networkidle' });

      await test.step('verify branding, header, and teletext styling', async () => {
        await expect(page).toHaveTitle(/Light Score/);
        await expect(page.getByText('Light Score')).toBeVisible();
        await expect(page.locator('.ttx-season-line')).toContainText(/20\d{2}/);
        await expect(page.getByText(/week \d+/i)).toBeVisible();

        const container = page.locator('.ttx-container');
        await expect(container).toBeVisible();
        await expect(container).toHaveCSS('font-family', /monospace/);
      });

      await test.step('verify only Upcoming Games panel is shown', async () => {
        await expect(
          page.getByRole('heading', { name: 'Upcoming Games' }),
        ).toBeVisible();
        await expect(page.locator('h2')).toHaveCount(1);

        await expect(page.getByRole('heading', { name: 'Live' })).toHaveCount(
          0,
        );
        await expect(
          page.getByRole('heading', { name: 'Games', exact: true }),
        ).toHaveCount(0);
        await expect(
          page.getByRole('heading', { name: 'Standings' }),
        ).toHaveCount(0);
        await expect(
          page.getByRole('heading', { name: 'Playoff Bracket' }),
        ).toHaveCount(0);
      });

      await test.step('verify no scores, live/final states, or navigation links', async () => {
        await expect(page.locator('.ttx-score')).toHaveCount(0);
        await expect(page.locator('.ttx-status-live')).toHaveCount(0);
        await expect(page.locator('.ttx-status-final')).toHaveCount(0);
        await expect(page.locator('.ttx-record')).toHaveCount(0);
        await expect(page.locator('a')).toHaveCount(0);
        await expect(page.getByRole('link', { name: /prev/i })).toHaveCount(0);
        await expect(page.getByRole('link', { name: /next/i })).toHaveCount(0);
      });

      await test.step('verify upcoming items or empty state', async () => {
        const panel = page.locator('.ttx-panel');
        const upcomingItems = panel.locator('.ttx-item:has(.ttx-teams)');
        const count = await upcomingItems.count();

        if (count > 0) {
          const first = upcomingItems.first();
          await expect(first.locator('.ttx-team')).toHaveCount(2);
          await expect(first.locator('.ttx-status-upcoming')).toBeVisible();
        } else {
          await expect(panel.getByText('No upcoming games')).toBeVisible();
        }
      });
    });
  });

  test('landing page does not link to /no-scores yet', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });
    await expect(page.locator('a[href*="/no-scores"]')).toHaveCount(0);
  });

  test('shows only upcoming games from mock regular_season fixture', async ({
    page,
  }) => {
    test.skip(!MOCK_MODE, 'MOCK_ESPN not set - skipping mock fixture check');

    await page.goto('/no-scores?year=2024&week=1&seasonType=3', {
      waitUntil: 'networkidle',
    });

    // Query params must be ignored; mock default is Regular Season Week 15
    await expect(page.locator('.ttx-season-line')).toContainText(
      'Regular Season',
    );
    await expect(page.getByText('Week 15')).toBeVisible();

    const upcomingItems = page.locator('.ttx-item:has(.ttx-teams)');
    await expect(upcomingItems).toHaveCount(2);

    // Upcoming games from regular_season.json are visible
    await expect(page.getByText('San Francisco 49ers')).toBeVisible();
    await expect(page.getByText('Los Angeles Rams')).toBeVisible();
    await expect(page.getByText('Mon 16.12. 03:20')).toBeVisible();
    await expect(page.getByText('Dallas Cowboys')).toBeVisible();
    await expect(page.getByText('Carolina Panthers')).toBeVisible();
    await expect(page.getByText('Mon 16.12. 20:00')).toBeVisible();

    // Final and live games from regular_season.json must not appear
    const excludedTeams = [
      'Kansas City Chiefs',
      'Las Vegas Raiders',
      'Buffalo Bills',
      'Detroit Lions',
      'Green Bay Packers',
      'Seattle Seahawks',
      'Philadelphia Eagles',
      'Pittsburgh Steelers',
    ];
    for (const team of excludedTeams) {
      await expect(page.getByText(team)).toHaveCount(0);
    }
  });
});
