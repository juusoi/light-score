import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET, BACKEND_ENV_SET } from './utils/env';

test.describe('Playoff Bracket - Mock Data', () => {
  // These tests require the services to be running with MOCK_ESPN=true
  test.skip(!FRONTEND_ENV_SET, 'SERVICE_URL not set - skipping UI tests');

  test.describe('Postseason View', () => {
    test.beforeEach(async ({ page }) => {
      // Navigate to postseason week 1 (Wild Card)
      await page.goto('/?seasonType=3&week=1', { waitUntil: 'networkidle' });
    });

    test('displays playoff bracket panel instead of standings', async ({
      page,
    }) => {
      await test.step('verify bracket panel is visible', async () => {
        await expect(
          page.getByRole('heading', { name: 'Playoff Bracket' }),
        ).toBeVisible();
      });

      await test.step('verify standings panel is hidden', async () => {
        // Standings heading should not be visible in postseason
        const standingsHeading = page.getByRole('heading', {
          name: 'Standings',
        });
        await expect(standingsHeading).not.toBeVisible();
      });
    });

    test('shows AFC and NFC conference sections', async ({ page }) => {
      await test.step('verify AFC section', async () => {
        await expect(page.getByRole('heading', { name: 'AFC' })).toBeVisible();
      });

      await test.step('verify NFC section', async () => {
        await expect(page.getByRole('heading', { name: 'NFC' })).toBeVisible();
      });

      await test.step('verify Super Bowl section', async () => {
        await expect(
          page.getByRole('heading', { name: 'Super Bowl' }),
        ).toBeVisible();
      });
    });

    test('displays playoff seeds with proper formatting', async ({ page }) => {
      await test.step('verify seed numbers are displayed', async () => {
        // Should have seed numbers like (1), (2), etc.
        const seedNums = page.locator('.ttx-seed-num');
        await expect(seedNums.first()).toBeVisible();
        await expect(seedNums.first()).toContainText(/\(\d+\)/);
      });

      await test.step('verify team abbreviations are shown', async () => {
        const seedTeams = page.locator('.ttx-seed-team');
        await expect(seedTeams.first()).toBeVisible();
      });

      await test.step('verify eliminated teams are styled', async () => {
        // Some teams should be eliminated (have strikethrough)
        const eliminatedSeeds = page.locator('.ttx-seed.ttx-eliminated');
        const count = await eliminatedSeeds.count();
        // In mock data, some teams are eliminated
        expect(count).toBeGreaterThan(0);
      });
    });

    test('displays playoff games with round labels', async ({ page }) => {
      await test.step('verify round labels are present', async () => {
        const roundLabels = page.locator('.ttx-bracket-round');
        await expect(roundLabels.first()).toBeVisible();
      });

      await test.step('verify game matchups are displayed', async () => {
        const matchups = page.locator('.ttx-bracket-matchup');
        await expect(matchups.first()).toBeVisible();
      });

      await test.step('verify scores are displayed for completed games', async () => {
        const scores = page.locator('.ttx-game-score');
        await expect(scores.first()).toBeVisible();
      });
    });

    test('highlights winners correctly', async ({ page }) => {
      await test.step('verify winner highlighting is applied', async () => {
        // In mock data, some games have winners
        const winners = page.locator('.ttx-bracket-team.ttx-winner');
        const count = await winners.count();
        expect(count).toBeGreaterThan(0);
      });
    });

    test('shows games in correct order (Conference finals at top)', async ({
      page,
    }) => {
      await test.step('verify game order in AFC bracket', async () => {
        const afcSection = page.locator('.ttx-bracket-conference').first();
        const roundLabels = afcSection.locator('.ttx-bracket-round');
        const firstRound = await roundLabels.first().textContent();

        // First game should be Conference (round 3), not Wild Card (round 1)
        expect(firstRound?.toLowerCase()).toContain('conference');
      });
    });
  });

  test.describe('Different Playoff Rounds', () => {
    test('Wild Card round shows correct week context', async ({ page }) => {
      await page.goto('/?seasonType=3&week=1', { waitUntil: 'networkidle' });
      await expect(page.getByText(/week 1/i)).toBeVisible();
      await expect(page.getByText(/postseason/i)).toBeVisible();
    });

    test('Divisional round shows correct week context', async ({ page }) => {
      await page.goto('/?seasonType=3&week=2', { waitUntil: 'networkidle' });
      await expect(page.getByText(/week 2/i)).toBeVisible();
    });

    test('Conference round shows correct week context', async ({ page }) => {
      await page.goto('/?seasonType=3&week=3', { waitUntil: 'networkidle' });
      await expect(page.getByText(/week 3/i)).toBeVisible();
    });

    test('Super Bowl week shows correct week context', async ({ page }) => {
      await page.goto('/?seasonType=3&week=4', { waitUntil: 'networkidle' });
      await expect(page.getByText(/week 4/i)).toBeVisible();
    });
  });

  test.describe('Regular Season View', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/?seasonType=2&week=15', { waitUntil: 'networkidle' });
    });

    test('shows standings panel instead of bracket', async ({ page }) => {
      await test.step('verify standings is visible', async () => {
        await expect(
          page.getByRole('heading', { name: 'Standings' }),
        ).toBeVisible();
      });

      await test.step('verify bracket is not visible', async () => {
        const bracketHeading = page.getByRole('heading', {
          name: 'Playoff Bracket',
        });
        await expect(bracketHeading).not.toBeVisible();
      });
    });

    test('displays division standings', async ({ page }) => {
      // Mock standings data has divisions
      const divisions = page.locator('.ttx-subtitle');
      const count = await divisions.count();
      expect(count).toBeGreaterThan(0);
    });
  });
});

test.describe('Playoff Bracket - API', () => {
  test.skip(!BACKEND_ENV_SET, 'Backend not available - skipping API tests');

  test('backend returns playoff bracket data', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/playoffs/bracket',
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toHaveProperty('season_year');
    expect(data).toHaveProperty('afc_seeds');
    expect(data).toHaveProperty('nfc_seeds');
    expect(data).toHaveProperty('games');
  });

  test('backend returns mock games data', async ({ request }) => {
    const response = await request.get('http://localhost:8000/games/weekly');
    expect(response.ok()).toBeTruthy();

    const games = await response.json();
    expect(Array.isArray(games)).toBeTruthy();
    expect(games.length).toBeGreaterThan(0);

    // Verify game structure
    const game = games[0];
    expect(game).toHaveProperty('team_a');
    expect(game).toHaveProperty('team_b');
    expect(game).toHaveProperty('status');
  });

  test('backend returns mock standings data', async ({ request }) => {
    const response = await request.get('http://localhost:8000/standings/live');
    expect(response.ok()).toBeTruthy();

    const standings = await response.json();
    expect(Array.isArray(standings)).toBeTruthy();
    // Mock data has 32 teams
    expect(standings.length).toBe(32);
  });

  test('fixture parameter overrides default fixture', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly?fixture=postseason_wildcard',
    );
    expect(response.ok()).toBeTruthy();

    const games = await response.json();
    // Wildcard fixture has 6 games
    expect(games.length).toBe(6);
  });
});
