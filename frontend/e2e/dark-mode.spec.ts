import { test, expect } from '@playwright/test';

test.describe('Dark Mode', () => {
  test('should toggle dark mode', async ({ page }) => {
    await page.goto('/');

    // Find the theme toggle button
    const themeToggle = page.locator('button[aria-label*="theme"], button[aria-label*="Toggle"]');

    if (await themeToggle.count() > 0) {
      // Get initial state
      const html = page.locator('html');
      const initialDark = await html.evaluate((el) => el.classList.contains('dark'));

      // Click to toggle
      await themeToggle.first().click();

      // Wait for theme change
      await page.waitForTimeout(100);

      // Check that theme changed
      const newDark = await html.evaluate((el) => el.classList.contains('dark'));
      expect(newDark).not.toBe(initialDark);
    }
  });

  test('should persist dark mode preference', async ({ page }) => {
    await page.goto('/');

    // Set dark mode via localStorage
    await page.evaluate(() => {
      localStorage.setItem('theme', 'dark');
    });

    // Reload page
    await page.reload();

    // Check that dark mode is applied
    const html = page.locator('html');
    await expect(html).toHaveClass(/dark/);
  });

  test('should respect system preference', async ({ page }) => {
    // Set system to dark mode
    await page.emulateMedia({ colorScheme: 'dark' });

    // Clear any stored preference
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.removeItem('theme');
    });

    await page.reload();

    // Check that dark mode is applied based on system preference
    const html = page.locator('html');
    await expect(html).toHaveClass(/dark/);
  });
});
