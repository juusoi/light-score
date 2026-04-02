import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET, requireFrontendUrl } from './utils/env';

test.describe('External NFL Site - Navigation and Health Checks', () => {
  test.skip(
    !FRONTEND_ENV_SET,
    'SERVICE_URL not configured - skipping external navigation tests',
  );

  let serviceUrl: string;

  test.beforeAll(() => {
    serviceUrl = requireFrontendUrl();
  });

  let consoleMessages: string[] = [];

  test.beforeEach(async ({ page }) => {
    // Reset console messages for each test
    consoleMessages = [];

    // Set up console logging
    page.on('console', msg => {
      try {
        consoleMessages.push(`${msg.type()}: ${msg.text()}`);
      } catch (e) {
        // Silently ignore console logging errors
      }
    });
  });

  test.describe('@smoke', () => {
    test('external site loads successfully and has basic structure', async ({
      page,
    }, testInfo) => {
      await test.step('navigate to external site', async () => {
        const response = await page.goto(serviceUrl, {
          waitUntil: 'load',
          timeout: 30_000,
        });

        expect(response).not.toBeNull();
        expect(response?.status()).toBeLessThan(400);

        await testInfo.attach('response-status', {
          body: Buffer.from(String(response?.status())),
          contentType: 'text/plain',
        });
      });

      await test.step('handle cookie consent or modal dialogs', async () => {
        // Try to dismiss any consent banners or modals
        const dialogButtons = [
          page.getByRole('button', {
            name: /accept|agree|hyväksy|ok|close|sulje/i,
          }),
          page.locator('[data-dismiss="modal"]'),
          page.locator('.cookie-accept, .modal-close, .close-button'),
        ];

        for (const button of dialogButtons) {
          try {
            if ((await button.count()) > 0) {
              await button.first().click({ timeout: 2000 });
              await page.waitForTimeout(500);
              break;
            }
          } catch (e) {
            // Continue to next button type if this one fails
          }
        }
      });

      await test.step('verify page has meaningful content', async () => {
        const title = await page.title();
        expect(title.length).toBeGreaterThan(0);

        await testInfo.attach('page-title', {
          body: Buffer.from(title),
          contentType: 'text/plain',
        });

        // Verify page has substantial content
        const bodyText = await page.locator('body').innerText();
        expect(bodyText.length).toBeGreaterThan(50);
      });

      await test.step('verify NFL-related content is present', async () => {
        // Look for NFL-related keywords in the page content
        const pageContent = await page.textContent('body');
        const hasNflContent = /nfl|score|standings|team|game|football/i.test(
          pageContent || '',
        );

        expect(hasNflContent).toBeTruthy();
      });

      await test.step('capture page artifacts', async () => {
        // Capture console messages
        await testInfo.attach('console-logs', {
          body: Buffer.from(consoleMessages.join('\n')),
          contentType: 'text/plain',
        });

        // Capture screenshot
        await testInfo.attach('page-screenshot', {
          body: await page.screenshot({ fullPage: true }),
          contentType: 'image/png',
        });

        // Capture HTML for debugging if needed
        await testInfo.attach('page-html', {
          body: Buffer.from(await page.content()),
          contentType: 'text/html',
        });
      });
    });
  });

  test('external site has proper semantic structure', async ({
    page,
  }, testInfo) => {
    await test.step('navigate and prepare page', async () => {
      await page.goto(serviceUrl, { waitUntil: 'load', timeout: 30_000 });

      // Handle consent dialogs
      const acceptButton = page.getByRole('button', {
        name: /accept|agree|hyväksy/i,
      });
      if ((await acceptButton.count()) > 0) {
        await acceptButton
          .first()
          .click()
          .catch(() => {});
      }

      await page.waitForTimeout(1000);
    });

    await test.step('verify semantic HTML structure', async () => {
      // Check for main content area
      const main = page.getByRole('main');
      const mainCount = await main.count();

      if (mainCount > 0) {
        // Main element should contain relevant content
        const mainText = await main.textContent();
        expect(mainText?.length).toBeGreaterThan(10);

        await testInfo.attach('main-content', {
          body: Buffer.from(mainText || ''),
          contentType: 'text/plain',
        });
      } else {
        // If no main element, body should still have substantial content
        const bodyText = await page.locator('body').textContent();
        expect(bodyText?.length).toBeGreaterThan(50);
      }
    });

    await test.step('verify headings and navigation', async () => {
      // Should have some heading structure
      const headings = await page.locator('h1, h2, h3, h4, h5, h6').count();
      expect(headings).toBeGreaterThan(0);

      // Should have some links for navigation
      const links = await page.getByRole('link').count();
      expect(links).toBeGreaterThan(0);
    });
  });
});
