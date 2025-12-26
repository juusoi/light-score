import { test, expect } from "@playwright/test";
import { FRONTEND_URL, BACKEND_URL, REQUIRE_FRONTEND } from "./utils/env";

test.describe("Playoff Picture Page", () => {
  test.skip(!REQUIRE_FRONTEND(), "SERVICE_URL not set");
  const frontendUrl = FRONTEND_URL;
  const backendUrl = BACKEND_URL;

  test("playoff picture page loads successfully", async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    await expect(page).toHaveTitle(/Light Score/);
    await expect(page.getByText("Playoff Picture")).toBeVisible();
  });

  test("playoff picture has season type navigation", async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    await expect(page.getByRole("link", { name: "Regular Season" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Postseason" })).toBeVisible();
  });

  test("playoff picture shows conference sections", async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    await expect(page.getByRole("heading", { name: "AFC" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "NFC" })).toBeVisible();
  });

  test("regular season view shows playoff race categories", async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs?seasonType=2`);
    // Regular season should show clinched, in the hunt, and eliminated categories
    await expect(page.getByText("Clinched")).toBeVisible();
    await expect(page.getByText("In the Hunt")).toBeVisible();
  });

  test("postseason view shows bracket status categories", async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs?seasonType=3`);
    // Postseason should show Super Bowl, Still Alive, and Eliminated categories
    await expect(page.getByText("Super Bowl")).toBeVisible();
    await expect(page.getByText("Still Alive")).toBeVisible();
    await expect(page.getByText("Eliminated")).toBeVisible();
  });

  test("back to scores link works", async ({ page }) => {
    await page.goto(`${frontendUrl}/playoffs`);
    const backLink = page.getByRole("link", { name: /Back to Scores/i });
    await expect(backLink).toBeVisible();
    await backLink.click();
    await expect(page).toHaveURL(frontendUrl + "/");
  });

  test("home page has link to playoff picture", async ({ page }) => {
    await page.goto(frontendUrl);
    const playoffLink = page.getByRole("link", { name: /Playoff Picture/i });
    await expect(playoffLink).toBeVisible();
    await playoffLink.click();
    await expect(page).toHaveURL(/\/playoffs/);
  });

  test("API endpoint returns valid playoff picture data", async ({ request }) => {
    const response = await request.get(`${backendUrl}/playoffs/picture`);
    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty("season_year");
    expect(data).toHaveProperty("season_type");
    expect(data).toHaveProperty("afc_teams");
    expect(data).toHaveProperty("nfc_teams");
    expect(data).toHaveProperty("super_bowl_teams");
    expect(Array.isArray(data.afc_teams)).toBe(true);
    expect(Array.isArray(data.nfc_teams)).toBe(true);
  });

  test("API endpoint accepts seasonType parameter", async ({ request }) => {
    const response = await request.get(`${backendUrl}/playoffs/picture?seasonType=3`);
    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data.season_type).toBe(3);
  });
});

