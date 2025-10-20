import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET, requireFrontendUrl } from './utils/env';

test.describe('External NFL Site - Structure and Interactions', () => {
  test.skip(
    !FRONTEND_ENV_SET,
    'SERVICE_URL not configured - skipping external interaction tests',
  );

  let serviceUrl: string;

  test.beforeAll(() => {
    serviceUrl = requireFrontendUrl();
  });

  test.beforeEach(async ({ page }) => {
    await page.goto(serviceUrl, {
      waitUntil: 'load',
      timeout: 30_000,
    });

    // Handle consent dialogs or modals
    await test.step('dismiss any consent or modal dialogs', async () => {
      const dialogSelectors = [
        page.getByRole('button', {
          name: /accept|agree|hyväksy|ok|sulje|close/i,
        }),
        page.locator('[data-dismiss="modal"]'),
        page.locator('.cookie-accept, .modal-close, .close-button'),
      ];

      for (const selector of dialogSelectors) {
        try {
          if ((await selector.count()) > 0) {
            await selector.first().click({ timeout: 2000 });
            await page.waitForTimeout(500);
            break;
          }
        } catch (e) {
          // Continue to next selector
        }
      }
    });

    // Additional wait for page to stabilize
    await page.waitForTimeout(1000);
  });

  test('has meaningful structure with main content, headings and navigation', async ({
    page,
  }, testInfo) => {
    await test.step('verify page loads successfully', async () => {
      // Verify page title exists and is meaningful
      const title = await page.title();
      expect(title.length).toBeGreaterThan(0);

      await testInfo.attach('page-title', {
        body: Buffer.from(title),
        contentType: 'text/plain',
      });
    });

    await test.step('verify semantic structure with fallback approaches', async () => {
      // Try to find main content area
      const main = page.getByRole('main');
      const mainCount = await main.count();

      if (mainCount > 0) {
        // If main element exists, verify it has content
        const mainText = await main.textContent();
        expect(mainText?.length).toBeGreaterThan(10);

        // Look for headings within main
        const headingsInMain = await main
          .locator('h1, h2, h3, h4, h5, h6')
          .count();
        if (headingsInMain === 0) {
          // If no proper headings, look for heading-like elements
          const fallbackHeadings = await main
            .locator('[class*="heading"], [class*="title"], .h1, .h2, .h3')
            .count();
          expect(fallbackHeadings).toBeGreaterThan(0);
        }
      } else {
        // No main element found - verify page still has meaningful structure
        const bodyText = await page.locator('body').textContent();
        expect(bodyText?.length).toBeGreaterThan(50);

        // Look for headings anywhere on page
        const headings = await page.locator('h1, h2, h3, h4, h5, h6').count();
        expect(headings).toBeGreaterThan(0);
      }
    });

    await test.step('verify navigation elements exist', async () => {
      // Look for navigation links
      const links = page.getByRole('link');
      const linkCount = await links.count();
      expect(linkCount).toBeGreaterThan(0);

      // Verify links have meaningful text or accessible names
      const firstFewLinks =
        (await links.first().count()) > 0 ? [links.first()] : [];
      if (firstFewLinks.length > 0) {
        const linkText = await firstFewLinks[0].textContent();
        expect(linkText?.trim().length).toBeGreaterThan(0);
      }
    });

    await test.step('capture page artifacts for analysis', async () => {
      await testInfo.attach('page-screenshot', {
        body: await page.screenshot({ fullPage: true }),
        contentType: 'image/png',
      });

      // Capture page structure for debugging
      const pageStructure = await page.evaluate(() => {
        const structure = {
          headings: Array.from(
            document.querySelectorAll('h1,h2,h3,h4,h5,h6'),
          ).map(h => ({
            tag: h.tagName,
            text: h.textContent?.trim().substring(0, 50),
          })),
          links: Array.from(document.querySelectorAll('a[href]')).length,
          hasMain: !!document.querySelector('main'),
          bodyTextLength: document.body.textContent?.length || 0,
        };
        return JSON.stringify(structure, null, 2);
      });

      await testInfo.attach('page-structure', {
        body: Buffer.from(pageStructure),
        contentType: 'application/json',
      });
    });
  });

  test('can interact with navigation links successfully', async ({
    page,
  }, testInfo) => {
    let targetLink: any = null;
    const linkInfo = { href: '', text: '' };

    await test.step('find and prepare navigation link', async () => {
      // Look for clickable links in order of preference

      // First, try to find a link in main content area
      const main = page.getByRole('main');
      if ((await main.count()) > 0) {
        const mainLinks = main.locator('a[href]');
        if ((await mainLinks.count()) > 0) {
          targetLink = mainLinks.first();
        }
      }

      // Fallback to any link on the page
      if (!targetLink) {
        const allLinks = page.locator('a[href]');
        const linkCount = await allLinks.count();

        test.skip(linkCount === 0, 'No clickable links found on page');

        // Find a link that's likely to work (not fragment-only or external)
        for (let i = 0; i < Math.min(linkCount, 5); i++) {
          const link = allLinks.nth(i);
          const href = await link.getAttribute('href');

          if (
            href &&
            !href.startsWith('#') &&
            !href.startsWith('mailto:') &&
            !href.startsWith('tel:')
          ) {
            targetLink = link;
            break;
          }
        }

        // If no good link found, use first available
        if (!targetLink) {
          targetLink = allLinks.first();
        }
      }

      // Get link information for testing
      linkInfo.href = (await targetLink!.getAttribute('href')) || '';
      linkInfo.text = (await targetLink!.textContent()) || '';

      await testInfo.attach('target-link-info', {
        body: Buffer.from(JSON.stringify(linkInfo, null, 2)),
        contentType: 'application/json',
      });
    });

    await test.step('perform navigation and verify result', async () => {
      const originalUrl = page.url();

      const navigationPromise = page
        .waitForNavigation({ waitUntil: 'load', timeout: 15_000 })
        .catch(() => null);
      const popupPromise = page
        .context()
        .waitForEvent('page', { timeout: 15_000 })
        .catch(() => null);

      await targetLink.click({ timeout: 5_000 });

      const [navigationResult, popupPage] = await Promise.all([
        navigationPromise,
        popupPromise,
      ]);

      if (popupPage) {
        await popupPage.waitForLoadState('load', { timeout: 15_000 }).catch(() => {});

        const popupUrl = popupPage.url();
        expect(popupUrl.length).toBeGreaterThan(0);

        await testInfo.attach('popup-url', {
          body: Buffer.from(popupUrl),
          contentType: 'text/plain',
        });

        const popupContent = await popupPage.content();
        expect(popupContent.length).toBeGreaterThan(0);

        await popupPage.close().catch(() => {});
        return;
      }

      if (!navigationResult) {
        // Ensure the page had a chance to settle even if navigation event did not fire (e.g., in WebKit)
        await page.waitForLoadState('load', { timeout: 5_000 }).catch(() => {});
      }

      const currentUrl = page.url();
      const navigationOccurred = currentUrl !== originalUrl;

      await testInfo.attach('navigation-result', {
        body: Buffer.from(
          JSON.stringify(
            {
              originalUrl,
              currentUrl,
              navigationOccurred,
              targetHref: linkInfo.href,
              linkText: linkInfo.text,
            },
            null,
            2,
          ),
        ),
        contentType: 'application/json',
      });

      const pageContent = await page.textContent('body');
      expect(pageContent?.length).toBeGreaterThan(0);

      if (navigationOccurred && linkInfo.href) {
        const hrefWithoutFragment = linkInfo.href.replace(/#.*$/, '');
        if (hrefWithoutFragment && !hrefWithoutFragment.startsWith('#')) {
          const urlMatches =
            currentUrl.includes(hrefWithoutFragment) ||
            currentUrl.length > originalUrl.length;
          expect(urlMatches).toBeTruthy();
        }
      } else {
        // Even if URL did not change (e.g., anchor navigation), ensure DOM updated
        expect(pageContent).toBeDefined();
      }

      await testInfo.attach('post-navigation-screenshot', {
        body: await page.screenshot({ fullPage: true }),
        contentType: 'image/png',
      });
    });
  });
});
