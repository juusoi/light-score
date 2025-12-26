import { test, expect } from '@playwright/test';
import { FRONTEND_URL, BACKEND_URL, REQUIRE_FRONTEND } from './utils/env';

test.describe('Playoff Picture Page (Regular Season)', () => {
  test.skip(!REQUIRE_FRONTEND(), 'SERVICE_URL not set');
  const frontendUrl = FRONTEND_URL;
  const backendUrl = BACKEND_URL;

  test('playoff picture page loads successfully', async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    await expect(page).toHaveTitle(/Light Score.*Playoff Seedings/);
    // Check that the page header shows "Playoff Seedings"
    await expect(page.getByText('Playoff Seedings')).toBeVisible();
  });

  test('playoff picture shows conference sections', async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    await expect(page.getByRole('heading', { name: 'AFC' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'NFC' })).toBeVisible();
  });

  test('regular season view shows playoff seedings', async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    // Regular season shows Playoff Seeds (1-7) and Outside Playoffs categories
    await expect(
      page.getByRole('heading', { name: 'Playoff Seeds' }).first(),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Outside Playoffs' }).first(),
    ).toBeVisible();
  });

  test('back to scores link works', async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    const backLink = page.getByRole('link', { name: /Back to Scores/i });
    await expect(backLink).toBeVisible();
    await backLink.click();
    await expect(page).toHaveURL(frontendUrl + '/');
  });

  test('home page has link to playoff picture in regular season', async ({
    page,
  }) => {
    // Navigate to regular season view
    await page.goto(`${frontendUrl}/?seasonType=2`);
    const playoffLink = page.getByRole('link', { name: /Playoff Picture/i });
    await expect(playoffLink).toBeVisible();
    await playoffLink.click();
    await expect(page).toHaveURL(/\/playoffs/);
  });

  test('home page does NOT have playoff picture link in postseason', async ({
    page,
  }) => {
    // Navigate to postseason view
    await page.goto(`${frontendUrl}/?seasonType=3`);
    const playoffLink = page.getByRole('link', { name: /Playoff Picture/i });
    await expect(playoffLink).not.toBeVisible();
  });

  test('API endpoint returns valid playoff picture data', async ({
    request,
  }) => {
    const response = await request.get(
      `${backendUrl}/playoffs/picture?seasonType=2`,
    );
    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty('season_year');
    expect(data).toHaveProperty('season_type');
    expect(data).toHaveProperty('afc_teams');
    expect(data).toHaveProperty('nfc_teams');
    expect(data).toHaveProperty('super_bowl_teams');
    expect(Array.isArray(data.afc_teams)).toBe(true);
    expect(Array.isArray(data.nfc_teams)).toBe(true);
    expect(data.season_type).toBe(2);
  });
});
