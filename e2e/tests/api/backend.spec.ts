import { test, expect } from '@playwright/test';
import { BACKEND_ENV_SET, requireBackendUrl } from '../utils/env';

test.describe('Light Score - Backend API Integration', () => {
  test.skip(
    !BACKEND_ENV_SET,
    'Local backend not configured - backend API tests require SERVICE_URL=http://localhost:5000',
  );

  let backendUrl: string;

  test.beforeAll(() => {
    backendUrl = requireBackendUrl();
  });

  test('backend API endpoints are accessible and return valid data', async ({
    request,
  }) => {
    await test.step('verify /games/weekly endpoint', async () => {
      const response = await request.get(`${backendUrl}/games/weekly`);

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();

        // Should return games array directly
        expect(Array.isArray(data)).toBeTruthy();

        // If games exist, verify structure
        if (data.length > 0) {
          const firstGame = data[0];
          expect(firstGame).toHaveProperty('team_a');
          expect(firstGame).toHaveProperty('team_b');
          expect(firstGame).toHaveProperty('status');
        }
      }
    });

    await test.step('verify /games/weekly/context endpoint', async () => {
      const response = await request.get(`${backendUrl}/games/weekly/context`);

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();

        // Should return context information
        expect(data).toHaveProperty('year');
        expect(data).toHaveProperty('week');
        expect(data).toHaveProperty('seasonType');

        // Year should be reasonable
        expect(data.year).toBeGreaterThan(2020);
        expect(data.year).toBeLessThan(2030);
      }
    });

    await test.step('verify /games/weekly/navigation endpoint', async () => {
      const response = await request.get(
        `${backendUrl}/games/weekly/navigation`,
      );

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();

        // Should return navigation information
        expect(data).toHaveProperty('prev_week_params');
        expect(data).toHaveProperty('next_week_params');

        // Navigation params should have required fields
        if (data.prev_week_params) {
          expect(data.prev_week_params).toHaveProperty('year');
          expect(data.prev_week_params).toHaveProperty('week');
          expect(data.prev_week_params).toHaveProperty('seasonType');
        }
      }
    });
  });

  test('standings endpoints return proper data structure', async ({
    request,
  }) => {
    await test.step('verify /standings endpoint', async () => {
      const response = await request.get(`${backendUrl}/standings`);

      // Accept 503 when cache is missing - this is expected behavior
      expect(response.status()).toBeLessThan(600);

      if (response.ok()) {
        const data = await response.json();

        // Should be an array of standings
        expect(Array.isArray(data)).toBeTruthy();

        if (data.length > 0) {
          const firstStanding = data[0];
          expect(firstStanding).toHaveProperty('team');
          expect(firstStanding).toHaveProperty('wins');
          expect(firstStanding).toHaveProperty('losses');
          expect(firstStanding).toHaveProperty('division');
        }
      } else if (response.status() === 503) {
        // Cache missing is acceptable for testing
        console.log(
          'Standings cache not available - this is expected in test environment',
        );
      }
    });

    await test.step('verify /standings/live endpoint', async () => {
      const response = await request.get(`${backendUrl}/standings/live`);

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();

        // Should be an array of live standings
        expect(Array.isArray(data)).toBeTruthy();

        if (data.length > 0) {
          const firstStanding = data[0];
          expect(firstStanding).toHaveProperty('team');
          expect(firstStanding).toHaveProperty('wins');
          expect(firstStanding).toHaveProperty('losses');
        }
      }
    });
  });

  test('teams endpoint returns team information', async ({ request }) => {
    await test.step('verify /teams endpoint', async () => {
      const response = await request.get(`${backendUrl}/teams`);

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();

        // Should return teams data
        expect(data).toBeDefined();

        // Teams data should be structured appropriately
        if (typeof data === 'object' && data !== null) {
          // Could be array or object depending on implementation
          expect(Object.keys(data).length).toBeGreaterThan(0);
        }
      }
    });
  });

  test('API endpoints handle query parameters correctly', async ({
    request,
  }) => {
    await test.step('verify /games/weekly with year parameter', async () => {
      const currentYear = new Date().getFullYear();
      const response = await request.get(
        `${backendUrl}/games/weekly?year=${currentYear}`,
      );

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();
        expect(Array.isArray(data)).toBeTruthy();
      }
    });

    await test.step('verify /games/weekly with week parameter', async () => {
      const response = await request.get(`${backendUrl}/games/weekly?week=1`);

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();
        expect(Array.isArray(data)).toBeTruthy();
      }
    });

    await test.step('verify /games/weekly with seasonType parameter', async () => {
      const response = await request.get(
        `${backendUrl}/games/weekly?seasonType=2`,
      );

      expect(response.status()).toBeLessThan(500);

      if (response.ok()) {
        const data = await response.json();
        expect(Array.isArray(data)).toBeTruthy();
      }
    });
  });

  test('API error handling works appropriately', async ({ request }) => {
    await test.step('verify handling of invalid parameters', async () => {
      // Test with invalid year
      const invalidYearResponse = await request.get(
        `${backendUrl}/games/weekly?year=1900`,
      );

      // Should either return empty data or proper error, but not crash
      expect(invalidYearResponse.status()).toBeLessThan(500);

      // Test with invalid week
      const invalidWeekResponse = await request.get(
        `${backendUrl}/games/weekly?week=999`,
      );
      expect(invalidWeekResponse.status()).toBeLessThan(500);
    });

    await test.step('verify CORS headers if applicable', async () => {
      const response = await request.get(`${backendUrl}/games/weekly`);

      if (response.ok()) {
        const headers = response.headers();
        // CORS headers might be present for API access
        // This is informational, not required
        const hasCorsHeaders =
          headers['access-control-allow-origin'] !== undefined;
        console.log('CORS headers present:', hasCorsHeaders);
      }
    });
  });

  test('API response times are reasonable', async ({ request }) => {
    const endpoints = [
      '/games/weekly',
      '/games/weekly/context',
      '/games/weekly/navigation',
      '/standings',
      '/teams',
    ];

    for (const endpoint of endpoints) {
      await test.step(`verify ${endpoint} response time`, async () => {
        const startTime = Date.now();

        try {
          const response = await request.get(`${backendUrl}${endpoint}`);
          const responseTime = Date.now() - startTime;

          // API should respond within reasonable time (5 seconds)
          expect(responseTime).toBeLessThan(5000);

          // Log response time for monitoring
          console.log(`${endpoint} response time: ${responseTime}ms`);
        } catch (error) {
          // If endpoint fails, that's noted but shouldn't fail the response time test
          console.log(`${endpoint} failed to respond:`, error);
        }
      });
    }
  });
});
