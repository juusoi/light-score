/**
 * Universal E2E tests for playoff bracket functionality.
 *
 * These tests verify UI structure and behavior, NOT specific data values.
 * They work with both mock data and production/live data.
 */
import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET, BACKEND_ENV_SET } from './utils/env';

test.describe('Playoff Bracket - UI Structure', () => {
  test.skip(!FRONTEND_ENV_SET, 'SERVICE_URL not set - skipping UI tests');

  test.describe('Postseason View (seasonType=3)', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/?seasonType=3&week=1', { waitUntil: 'networkidle' });
    });

    test('displays playoff bracket panel instead of standings', async ({
      page,
    }) => {
      // In postseason, bracket should be visible
      const bracketHeading = page.getByRole('heading', {
        name: 'Playoff Bracket',
      });
      const standingsHeading = page.getByRole('heading', { name: 'Standings' });

      // Either bracket is shown (postseason data available) or standings fallback
      const hasBracket = await bracketHeading.isVisible().catch(() => false);
      const hasStandings = await standingsHeading
        .isVisible()
        .catch(() => false);

      // One of them must be visible
      expect(hasBracket || hasStandings).toBeTruthy();

      // If bracket is visible, standings should not be
      if (hasBracket) {
        await expect(standingsHeading).not.toBeVisible();
      }
    });

    test('shows conference sections when bracket data available', async ({
      page,
    }) => {
      const bracketPanel = page.locator('.ttx-bracket-panel');
      const hasBracket = await bracketPanel.isVisible().catch(() => false);

      if (hasBracket) {
        await expect(page.getByRole('heading', { name: 'AFC' })).toBeVisible();
        await expect(page.getByRole('heading', { name: 'NFC' })).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Super Bowl' }),
        ).toBeVisible();
      }
    });

    test('displays seeds with proper structure when available', async ({
      page,
    }) => {
      const seeds = page.locator('.ttx-seed');
      const seedCount = await seeds.count();

      if (seedCount > 0) {
        // Seeds should have number and team abbreviation
        const firstSeed = seeds.first();
        await expect(firstSeed.locator('.ttx-seed-num')).toBeVisible();
        await expect(firstSeed.locator('.ttx-seed-team')).toBeVisible();
      }
    });

    test('displays games with proper structure when available', async ({
      page,
    }) => {
      const games = page.locator('.ttx-bracket-game');
      const gameCount = await games.count();

      if (gameCount > 0) {
        const firstGame = games.first();
        // Games should have round label, matchup, and status
        await expect(firstGame.locator('.ttx-bracket-round')).toBeVisible();
        await expect(firstGame.locator('.ttx-bracket-matchup')).toBeVisible();
        await expect(firstGame.locator('.ttx-bracket-status')).toBeVisible();
      }
    });

    test('shows correct week in postseason context', async ({ page }) => {
      await expect(page.getByText(/week 1/i)).toBeVisible();
      await expect(page.getByText(/postseason/i)).toBeVisible();
    });
  });

  test.describe('Regular Season View (seasonType=2)', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/?seasonType=2', { waitUntil: 'networkidle' });
    });

    test('shows standings panel instead of bracket', async ({ page }) => {
      await expect(
        page.getByRole('heading', { name: 'Standings' }),
      ).toBeVisible();

      const bracketHeading = page.getByRole('heading', {
        name: 'Playoff Bracket',
      });
      await expect(bracketHeading).not.toBeVisible();
    });

    test('shows regular season in context', async ({ page }) => {
      await expect(page.getByText(/regular season/i)).toBeVisible();
    });
  });

  test.describe('Week Navigation in Postseason', () => {
    test('can navigate between playoff weeks', async ({ page }) => {
      await page.goto('/?seasonType=3&week=1', { waitUntil: 'networkidle' });

      const nextLink = page.getByRole('link', { name: /next/i });
      await expect(nextLink).toBeVisible();
      await expect(nextLink).toHaveAttribute('href', /week=2/);
    });

    test('maintains seasonType when navigating', async ({ page }) => {
      await page.goto('/?seasonType=3&week=2', { waitUntil: 'networkidle' });

      const prevLink = page.getByRole('link', { name: /prev/i });
      const nextLink = page.getByRole('link', { name: /next/i });

      await expect(prevLink).toHaveAttribute('href', /seasonType=3/);
      await expect(nextLink).toHaveAttribute('href', /seasonType=3/);
    });
  });
});

test.describe('Playoff Bracket - API Structure', () => {
  test.skip(!BACKEND_ENV_SET, 'Backend not available - skipping API tests');

  test('bracket endpoint returns valid structure', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/playoffs/bracket',
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('season_year');
    expect(data).toHaveProperty('afc_seeds');
    expect(data).toHaveProperty('nfc_seeds');
    expect(data).toHaveProperty('games');
    expect(Array.isArray(data.afc_seeds)).toBeTruthy();
    expect(Array.isArray(data.nfc_seeds)).toBeTruthy();
    expect(Array.isArray(data.games)).toBeTruthy();
  });

  test('games endpoint returns valid structure', async ({ request }) => {
    const response = await request.get('http://localhost:8000/games/weekly');
    expect(response.ok()).toBeTruthy();

    const games = await response.json();
    expect(Array.isArray(games)).toBeTruthy();

    if (games.length > 0) {
      const game = games[0];
      expect(game).toHaveProperty('team_a');
      expect(game).toHaveProperty('team_b');
      expect(game).toHaveProperty('status');
      expect(game).toHaveProperty('start_time');
    }
  });

  test('standings endpoint returns valid structure', async ({ request }) => {
    const response = await request.get('http://localhost:8000/standings/live');
    expect(response.ok()).toBeTruthy();

    const standings = await response.json();
    expect(Array.isArray(standings)).toBeTruthy();

    if (standings.length > 0) {
      const team = standings[0];
      expect(team).toHaveProperty('team');
      expect(team).toHaveProperty('wins');
      expect(team).toHaveProperty('losses');
      expect(team).toHaveProperty('division');
    }
  });

  test('context endpoint returns valid structure', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly/context?seasonType=3&week=1',
    );
    expect(response.ok()).toBeTruthy();

    const ctx = await response.json();
    expect(ctx).toHaveProperty('year');
    expect(ctx).toHaveProperty('week');
    expect(ctx).toHaveProperty('seasonType');
  });
});
