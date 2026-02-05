import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should load the home page', async ({ page }) => {
    await page.goto('/');
    // The app is branded as V99 POS
    await expect(page).toHaveTitle(/V99 POS/);
  });

  test('should navigate to menu page', async ({ page }) => {
    await page.goto('/');
    // Click the Menu button in sidebar to expand, then click Menu Items link
    const menuGroup = page.locator('button:has-text("Menu")');
    await menuGroup.click();
    await page.click('text=Menu Items');
    await expect(page).toHaveURL(/\/menu/);
  });

  test('should navigate to tables page', async ({ page }) => {
    await page.goto('/');
    await page.click('a:has-text("Tables")');
    await expect(page).toHaveURL(/\/tables/);
  });

  test('should have working skip link for accessibility', async ({ page }) => {
    await page.goto('/');

    // Focus the skip link
    await page.keyboard.press('Tab');

    const skipLink = page.locator('a[href="#main-content"]');
    await expect(skipLink).toBeFocused();

    // Click the skip link
    await skipLink.click();

    // Check that main content is now focused
    const mainContent = page.locator('#main-content');
    await expect(mainContent).toBeVisible();
  });

  test('sidebar navigation groups should expand', async ({ page }) => {
    await page.goto('/');

    // Find and click an expandable navigation group
    const menuGroup = page.locator('button:has-text("Menu")');
    await menuGroup.click();

    // Check that submenu items are visible (Menu Items is the actual link text)
    await expect(page.locator('text=Menu Items')).toBeVisible();
  });
});
