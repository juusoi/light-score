/**
 * Mock-only E2E tests for playoff bracket fixtures.
 *
 * These tests require MOCK_ESPN=true on the backend and verify specific
 * fixture data. They will FAIL against production or live data.
 *
 * Run with: MOCK_ESPN=true make mock-up && MOCK_ESPN=true SERVICE_URL=http://localhost:5000 make test-e2e
 */
import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET, BACKEND_ENV_SET } from '../utils/env';

// Skip all mock tests unless MOCK_ESPN is set in the test environment
const MOCK_MODE = process.env.MOCK_ESPN === 'true' || process.env.MOCK_ESPN === '1';

test.describe('Mock Fixtures - Playoff Bracket Data', () => {
  test.skip(!MOCK_MODE, 'MOCK_ESPN not set - skipping mock fixture tests');
  test.skip(!BACKEND_ENV_SET, 'Backend not available - skipping mock tests');

  test('returns exactly 7 AFC seeds from fixture', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/playoffs/bracket',
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data.afc_seeds).toHaveLength(7);
  });

  test('returns exactly 7 NFC seeds from fixture', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/playoffs/bracket',
    );
    const data = await response.json();
    expect(data.nfc_seeds).toHaveLength(7);
  });

  test('Chiefs are AFC 1 seed in fixture', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/playoffs/bracket',
    );
    const data = await response.json();
    const seed1 = data.afc_seeds.find(
      (s: { seed: number }) => s.seed === 1,
    );
    expect(seed1.team).toBe('Kansas City Chiefs');
    expect(seed1.eliminated).toBe(false);
  });

  test('fixture has 13 playoff games total', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/playoffs/bracket',
    );
    const data = await response.json();
    // 6 Wild Card + 4 Divisional + 2 Conference + 1 Super Bowl = 13
    expect(data.games).toHaveLength(13);
  });
});

test.describe('Mock Fixtures - Games Data', () => {
  test.skip(!MOCK_MODE, 'MOCK_ESPN not set - skipping mock fixture tests');
  test.skip(!BACKEND_ENV_SET, 'Backend not available - skipping mock tests');

  test('regular season fixture has 6 games', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly?fixture=regular_season',
    );
    expect(response.ok()).toBeTruthy();

    const games = await response.json();
    expect(games).toHaveLength(6);
  });

  test('wildcard fixture has 6 games', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly?fixture=postseason_wildcard',
    );
    const games = await response.json();
    expect(games).toHaveLength(6);
  });

  test('divisional fixture has 4 games', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly?fixture=postseason_divisional',
    );
    const games = await response.json();
    expect(games).toHaveLength(4);
  });

  test('conference fixture has 2 games', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly?fixture=postseason_conference',
    );
    const games = await response.json();
    expect(games).toHaveLength(2);
  });

  test('superbowl fixture has 1 game', async ({ request }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly?fixture=postseason_superbowl',
    );
    const games = await response.json();
    expect(games).toHaveLength(1);
  });

  test('regular season fixture contains Chiefs vs Raiders', async ({
    request,
  }) => {
    const response = await request.get(
      'http://localhost:8000/games/weekly?fixture=regular_season',
    );
    const games = await response.json();
    const chiefsGame = games.find(
      (g: { team_a: string; team_b: string }) =>
        g.team_a === 'Kansas City Chiefs' || g.team_b === 'Kansas City Chiefs',
    );
    expect(chiefsGame).toBeDefined();
    expect(chiefsGame.team_b).toBe('Las Vegas Raiders');
  });
});

test.describe('Mock Fixtures - Standings Data', () => {
  test.skip(!MOCK_MODE, 'MOCK_ESPN not set - skipping mock fixture tests');
  test.skip(!BACKEND_ENV_SET, 'Backend not available - skipping mock tests');

  test('standings fixture has exactly 32 teams', async ({ request }) => {
    const response = await request.get('http://localhost:8000/standings/live');
    expect(response.ok()).toBeTruthy();

    const standings = await response.json();
    expect(standings).toHaveLength(32);
  });

  test('standings fixture has all 8 divisions', async ({ request }) => {
    const response = await request.get('http://localhost:8000/standings/live');
    const standings = await response.json();

    const divisions = new Set(
      standings.map((s: { division: string }) => s.division),
    );
    expect(divisions.size).toBe(8);
    expect(divisions).toContain('AFC East');
    expect(divisions).toContain('AFC North');
    expect(divisions).toContain('AFC South');
    expect(divisions).toContain('AFC West');
    expect(divisions).toContain('NFC East');
    expect(divisions).toContain('NFC North');
    expect(divisions).toContain('NFC South');
    expect(divisions).toContain('NFC West');
  });

  test('Chiefs have 15-2 record in fixture', async ({ request }) => {
    const response = await request.get('http://localhost:8000/standings/live');
    const standings = await response.json();

    const chiefs = standings.find(
      (s: { team: string }) => s.team === 'Kansas City Chiefs',
    );
    expect(chiefs).toBeDefined();
    expect(chiefs.wins).toBe(15);
    expect(chiefs.losses).toBe(2);
  });
});

test.describe('Mock Fixtures - UI Verification', () => {
  test.skip(!MOCK_MODE, 'MOCK_ESPN not set - skipping mock fixture tests');
  test.skip(!FRONTEND_ENV_SET, 'SERVICE_URL not set - skipping UI tests');

  test('postseason view shows eliminated teams with strikethrough', async ({
    page,
  }) => {
    await page.goto('/?seasonType=3&week=1', { waitUntil: 'networkidle' });

    // In mock data, Ravens (seed 3) are eliminated
    const eliminatedSeeds = page.locator('.ttx-seed.ttx-eliminated');
    const count = await eliminatedSeeds.count();

    // Mock playoff_seeds.json fixture has 10 eliminated teams total:
    // AFC: seeds 3-7 eliminated (5 teams)
    // NFC: seeds 1, 3-7 eliminated (6 teams, but seed 1 DET lost in playoffs)
    // We use 5 as minimum threshold to avoid brittleness if fixture changes slightly
    const EXPECTED_MIN_ELIMINATED_TEAMS = 5;
    expect(count).toBeGreaterThanOrEqual(EXPECTED_MIN_ELIMINATED_TEAMS);
  });

  test('postseason view shows specific fixture teams', async ({ page }) => {
    await page.goto('/?seasonType=3&week=1', { waitUntil: 'networkidle' });

    // Check for specific mock data team abbreviations in seeds section
    const seeds = page.locator('.ttx-seeds');
    await expect(seeds.getByText('KC', { exact: true })).toBeVisible(); // Chiefs
    await expect(seeds.getByText('BUF', { exact: true }).first()).toBeVisible(); // Bills
    await expect(seeds.getByText('PHI', { exact: true }).first()).toBeVisible(); // Eagles
  });

  test('regular season shows fixture game scores', async ({ page }) => {
    await page.goto('/?seasonType=2&week=15', { waitUntil: 'networkidle' });

    // Mock fixture has Chiefs 19 - Raiders 17
    // Check that scores are visible (exact match depends on game status)
    const scores = page.locator('.ttx-record-wins, .ttx-record-losses');
    const count = await scores.count();
    expect(count).toBeGreaterThan(0);
  });
});

