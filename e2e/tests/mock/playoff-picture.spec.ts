/**
 * Mock-specific E2E tests for the Playoff Picture page.
 * These tests verify specific mock fixture data values.
 * Only run with MOCK_ESPN=true.
 *
 * Run with: MOCK_ESPN=true make mock-up && MOCK_ESPN=true SERVICE_URL=http://localhost:5000 make test-e2e
 */
import { test, expect } from "@playwright/test";
import { FRONTEND_URL, BACKEND_URL, REQUIRE_FRONTEND } from "../utils/env";

// Skip all mock tests unless MOCK_ESPN is set in the test environment
const MOCK_MODE = process.env.MOCK_ESPN === "true" || process.env.MOCK_ESPN === "1";

test.describe("Playoff Picture - Mock Data Verification", () => {
  test.skip(!MOCK_MODE, "MOCK_ESPN not set - skipping mock tests");
  test.skip(!REQUIRE_FRONTEND(), "SERVICE_URL not set");
  const frontendUrl = FRONTEND_URL;
  const backendUrl = BACKEND_URL;

  test.describe("Regular Season Playoff Race", () => {
    test("shows 16 AFC teams", async ({ request }) => {
      const response = await request.get(
        `${backendUrl}/playoffs/picture?seasonType=2`
      );
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(data.afc_teams).toHaveLength(16);
    });

    test("shows 16 NFC teams", async ({ request }) => {
      const response = await request.get(
        `${backendUrl}/playoffs/picture?seasonType=2`
      );
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(data.nfc_teams).toHaveLength(16);
    });

    test("top 7 teams in each conference have seeds", async ({ request }) => {
      const response = await request.get(
        `${backendUrl}/playoffs/picture?seasonType=2`
      );
      expect(response.ok()).toBe(true);
      const data = await response.json();

      // Check AFC seeds 1-7
      const afcSeeded = data.afc_teams.filter(
        (t: { seed: number | null }) => t.seed !== null
      );
      expect(afcSeeded.length).toBe(7);

      // Check NFC seeds 1-7
      const nfcSeeded = data.nfc_teams.filter(
        (t: { seed: number | null }) => t.seed !== null
      );
      expect(nfcSeeded.length).toBe(7);
    });

    test("displays team win-loss records", async ({ page }) => {
      await page.goto(`${frontendUrl}/playoffs?seasonType=2`);
      // Check for record format (wins-losses)
      const recordPattern = /\d+-\d+/;
      const content = await page.textContent(".ttx-playoff-picture");
      expect(content).toMatch(recordPattern);
    });
  });

  test.describe("Postseason Bracket Status", () => {
    test("shows exactly 7 AFC seeds", async ({ request }) => {
      const response = await request.get(
        `${backendUrl}/playoffs/picture?seasonType=3`
      );
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(data.afc_teams).toHaveLength(7);
    });

    test("shows exactly 7 NFC seeds", async ({ request }) => {
      const response = await request.get(
        `${backendUrl}/playoffs/picture?seasonType=3`
      );
      expect(response.ok()).toBe(true);
      const data = await response.json();
      expect(data.nfc_teams).toHaveLength(7);
    });

    test("eliminated teams have eliminated status", async ({ request }) => {
      const response = await request.get(
        `${backendUrl}/playoffs/picture?seasonType=3`
      );
      expect(response.ok()).toBe(true);
      const data = await response.json();

      // At least some teams should be eliminated in mock postseason data
      const eliminatedAfc = data.afc_teams.filter(
        (t: { status: string }) => t.status === "eliminated"
      );
      const eliminatedNfc = data.nfc_teams.filter(
        (t: { status: string }) => t.status === "eliminated"
      );

      // Based on mock data, we expect several eliminated teams
      expect(eliminatedAfc.length + eliminatedNfc.length).toBeGreaterThan(0);
    });

    test("super bowl teams are identified", async ({ request }) => {
      const response = await request.get(
        `${backendUrl}/playoffs/picture?seasonType=3`
      );
      expect(response.ok()).toBe(true);
      const data = await response.json();

      // Based on mock data with Super Bowl game
      expect(data.super_bowl_teams).toBeDefined();
      expect(Array.isArray(data.super_bowl_teams)).toBe(true);
    });

    test("displays eliminated teams with strikethrough styling", async ({
      page,
    }) => {
      await page.goto(`${frontendUrl}/playoffs?seasonType=3`);
      const eliminatedTeam = page.locator(".ttx-eliminated-team").first();
      await expect(eliminatedTeam).toBeVisible();
    });
  });
});

