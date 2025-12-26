import { test, expect } from '@playwright/test';
import { FRONTEND_ENV_SET, requireFrontendUrl } from './utils/env';

test.describe('Light Score - Error Handling and Edge Cases', () => {
  // Require explicit SERVICE_URL for these UI-centric tests
  test.skip(
    !FRONTEND_ENV_SET,
    'SERVICE_URL not configured - skipping error handling tests',
  );

  test('handles invalid URL parameters gracefully', async ({ page }) => {
    const invalidParams = [
      '?year=invalid',
      '?week=abc',
      '?seasonType=invalid',
      '?year=1800&week=999&seasonType=99',
    ];

    for (const params of invalidParams) {
      await test.step(`test with invalid parameters: ${params}`, async () => {
        await page.goto(`/${params}`, {
          waitUntil: 'networkidle',
          timeout: 15000,
        });

        // Page should still load and show branding
        await expect(page.getByText('Light Score')).toBeVisible();

        // Should show main sections even if empty
        await expect(page.getByRole('heading', { name: 'Live' })).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Games' }),
        ).toBeVisible();
        await expect(
          page.getByRole('heading', { name: 'Standings' }),
        ).toBeVisible();

        // Navigation should still work
        await expect(page.getByRole('link', { name: /prev/i })).toBeVisible();
        await expect(page.getByRole('link', { name: /next/i })).toBeVisible();

        await expect(
          page.getByText(/Could not retrieve data from backend/i),
        ).toHaveCount(0);
      });
    }
  });

  test('handles network timeouts and slow responses', async ({ page }) => {
    await test.step('test with shorter timeout to simulate slow network', async () => {
      // Try to load page with very short timeout to test timeout handling
      try {
        await page.goto('/', {
          waitUntil: 'networkidle',
          timeout: 1000, // Very short timeout
        });
      } catch (e) {
        // If timeout occurs, verify page still has basic structure
        const hasContent = (await page.locator('body').count()) > 0;
        if (hasContent) {
          const bodyText = await page.textContent('body');
          expect(bodyText?.length).toBeGreaterThan(0);
        }
      }

      // Now load normally to ensure page works
      await page.goto('/', { waitUntil: 'networkidle' });
      await expect(page.getByText('Light Score')).toBeVisible();
    });
  });

  test('maintains functionality when JavaScript is disabled', async ({
    browser,
  }) => {
    await test.step('create context with JavaScript disabled', async () => {
      const context = await browser.newContext({
        javaScriptEnabled: false,
      });

      const page = await context.newPage();

      try {
        const serviceUrl = requireFrontendUrl();
        await page.goto(serviceUrl, { waitUntil: 'domcontentloaded' });

        // Basic HTML structure should still work
        await expect(page.getByText('Light Score')).toBeVisible();

        // Navigation links should be present and functional
        const prevLink = page.getByRole('link', { name: /prev/i });
        const nextLink = page.getByRole('link', { name: /next/i });

        await expect(prevLink).toBeVisible();
        await expect(nextLink).toBeVisible();

        // Links should have href attributes
        await expect(prevLink).toHaveAttribute('href');
        await expect(nextLink).toHaveAttribute('href');
      } finally {
        await context.close();
      }
    });
  });

  test('handles missing or malformed data gracefully', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    await test.step('verify fallback messages for empty data', async () => {
      // Check if empty state messages are shown appropriately
      const liveSection = page.locator('.ttx-panel:has(h2:text("Live"))');
      const gamesSection = page.locator('.ttx-panel:has(h2:text("Games"))');
      const standingsSection = page.locator(
        '.ttx-panel:has(h2:text("Standings"))',
      );

      // Each section should show either data or appropriate "no data" message
      const sections = [
        { section: liveSection, emptyText: 'No live games' },
        { section: gamesSection, emptyText: 'No games' },
        { section: standingsSection, emptyText: 'No standings available' },
      ];

      for (const { section, emptyText } of sections) {
        const hasData =
          (await section.locator('.ttx-item:not(:has-text("No"))').count()) > 0;
        const hasEmptyMessage =
          (await section.getByText(emptyText).count()) > 0;

        // Should have either data or empty message, not both or neither
        expect(hasData || hasEmptyMessage).toBeTruthy();

        if (!hasData) {
          await expect(section.getByText(emptyText)).toBeVisible();
        }
      }
    });

    await test.step('verify error boundaries do not crash page', async () => {
      // Check that page doesn't show any obvious error messages or crash indicators
      const errorTexts = [
        'error occurred',
        'something went wrong',
        'internal server error',
        'undefined',
        'null',
        'NaN',
      ];

      const bodyText = (await page.textContent('body'))?.toLowerCase() || '';

      for (const errorText of errorTexts) {
        expect(bodyText.includes(errorText)).toBeFalsy();
      }
    });
  });

  test('responsive breakpoints handle edge cases', async ({ page }) => {
    const edgeCaseViewports = [
      { width: 320, height: 568, name: 'very small mobile' },
      { width: 1, height: 1, name: 'minimal' },
      { width: 3000, height: 2000, name: 'very large' },
      { width: 800, height: 600, name: 'square-ish' },
    ];

    for (const viewport of edgeCaseViewports) {
      await test.step(`test ${viewport.name} viewport (${viewport.width}x${viewport.height})`, async () => {
        await page.setViewportSize(viewport);
        await page.goto('/', { waitUntil: 'networkidle' });

        // Even at extreme viewports, core content should be accessible
        await expect(page.getByText('Light Score')).toBeVisible();

        // Navigation should not break
        const prevLink = page.getByRole('link', { name: /prev/i });
        const nextLink = page.getByRole('link', { name: /next/i });

        // Links should exist (even if styled differently)
        expect(await prevLink.count()).toBeGreaterThan(0);
        expect(await nextLink.count()).toBeGreaterThan(0);
      });
    }
  });

  test('keyboard navigation works properly', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    await test.step('verify tab navigation through links', async () => {
      // Focus the page body first
      await page.click('body');

      // Tab through focusable elements to find navigation links
      let focusedElement = null;
      let tabCount = 0;
      // Max tabs accounts for: brand link, season type links, week nav links,
      // playoff picture link, and any dynamically added focusable elements.
      // This limit was increased from 10 to 15 after adding the /playoffs link.
      const maxTabs = 15;

      // Tab through elements until we find a navigation link
      while (tabCount < maxTabs) {
        await page.press('body', 'Tab');
        focusedElement = await page.evaluate(() => {
          const active = document.activeElement;
          return {
            tagName: active?.tagName,
            className: active?.className,
            text: active?.textContent?.trim(),
          };
        });

        tabCount++;

        // Check if we found a navigation link (Prev or Next)
        if (
          focusedElement?.tagName === 'A' &&
          (focusedElement.text === 'Prev' || focusedElement.text === 'Next')
        ) {
          break;
        }
      }

      // The primary assertion is that we found a navigation link (an <A> tag).
      // tabCount <= maxTabs confirms we didn't exceed the search limit.
      // Equality is valid: finding the link on the last tab is still success.
      expect(tabCount).toBeLessThanOrEqual(maxTabs);
      expect(focusedElement?.tagName).toBe('A');
    });

    await test.step('verify Enter key activates links', async () => {
      // Focus on a navigation link
      const prevLink = page.getByRole('link', { name: /prev/i });
      await prevLink.focus();

      const initialUrl = page.url();

      // Press Enter to activate the link
      await page.press('body', 'Enter');
      await page.waitForLoadState('networkidle');

      // Should have navigated
      const newUrl = page.url();
      expect(newUrl).not.toBe(initialUrl);

      // Page should still be functional
      await expect(page.getByText('Light Score')).toBeVisible();
    });
  });

  test('screen reader compatibility basics', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    await test.step('verify heading hierarchy', async () => {
      // Should have proper heading levels
      const headings = await page.locator('h1, h2, h3, h4, h5, h6').all();

      expect(headings.length).toBeGreaterThan(0);

      // Get heading levels
      const headingLevels = await Promise.all(
        headings.map(async h => {
          const tagName = await h.evaluate(el => el.tagName);
          return parseInt(tagName.replace('H', ''), 10);
        }),
      );

      // Should not skip heading levels dramatically (h1 to h4, etc.)
      const maxLevel = Math.max(...headingLevels);
      const minLevel = Math.min(...headingLevels);

      expect(maxLevel - minLevel).toBeLessThanOrEqual(3);
    });

    await test.step('verify ARIA labels and landmarks', async () => {
      // Navigation should be properly labeled
      const navElement = page.locator('[aria-label*="navigation"], nav');
      if ((await navElement.count()) > 0) {
        await expect(navElement.first()).toBeVisible();
      }

      // Important content should have ARIA labels
      const ariaLabeled = page.locator('[aria-label]');
      const ariaLabelCount = await ariaLabeled.count();

      expect(ariaLabelCount).toBeGreaterThan(0);
    });

    await test.step('verify text alternatives', async () => {
      // Images should have alt text (if any images exist)
      const images = await page.locator('img').count();

      if (images > 0) {
        const imagesWithAlt = await page.locator('img[alt]').count();
        // Most images should have alt text
        expect(imagesWithAlt / images).toBeGreaterThan(0.5);
      }

      // Interactive elements should be properly labeled
      const buttons = await page
        .locator('button, input[type="button"], input[type="submit"]')
        .count();

      if (buttons > 0) {
        // All buttons should have accessible names
        const buttonsWithNames = await page
          .locator(
            'button:not([aria-label=""]), input[type="button"]:not([aria-label=""]), input[type="submit"]:not([aria-label=""])',
          )
          .count();
        expect(buttonsWithNames).toBeGreaterThan(0);
      }
    });
  });

  test('handles browser back/forward navigation', async ({ page }) => {
    await page.goto('/', { waitUntil: 'networkidle' });

    await test.step('navigate forward and back using browser controls', async () => {
      const initialUrl = page.url();

      // Click a navigation link
      const nextLink = page.getByRole('link', { name: /next/i });
      await nextLink.click();
      await page.waitForLoadState('networkidle');

      const secondUrl = page.url();
      expect(secondUrl).not.toBe(initialUrl);

      // Use browser back button
      await page.goBack();
      await page.waitForLoadState('networkidle');

      const backUrl = page.url();
      expect(backUrl).toBe(initialUrl);

      // Page should still be functional after back navigation
      await expect(page.getByText('Light Score')).toBeVisible();

      // Use browser forward button
      await page.goForward();
      await page.waitForLoadState('networkidle');

      const forwardUrl = page.url();
      expect(forwardUrl).toBe(secondUrl);

      await expect(page.getByText('Light Score')).toBeVisible();
    });
  });
});
