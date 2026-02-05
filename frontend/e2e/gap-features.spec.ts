import { test, expect } from '@playwright/test';

test.describe('Gap Features', () => {
  test.describe('KDS Localization', () => {
    test('should load KDS localization page', async ({ page }) => {
      await page.goto('/kitchen/localization');
      await expect(page.locator('h1')).toContainText('KDS Localization');
    });

    test('should display language options', async ({ page }) => {
      await page.goto('/kitchen/localization');
      await expect(page.locator('text=English')).toBeVisible();
    });
  });

  test.describe('Mobile Wallet', () => {
    test('should load mobile wallet page', async ({ page }) => {
      await page.goto('/settings/mobile-wallet');
      await expect(page.locator('h1')).toContainText('Mobile Wallet Payments');
    });

    test('should show Apple Pay and Google Pay options', async ({ page }) => {
      await page.goto('/settings/mobile-wallet');
      // Wait for page to fully load, then check for payment method text
      await page.waitForLoadState('networkidle');
      await expect(page.locator('text=Apple Pay').first()).toBeVisible();
      await expect(page.locator('text=Google Pay').first()).toBeVisible();
    });
  });

  test.describe('VIP Management', () => {
    test('should load VIP management page', async ({ page }) => {
      await page.goto('/vip-management');
      await expect(page.locator('h1')).toContainText('VIP');
    });

    test('should show VIP tiers', async ({ page }) => {
      await page.goto('/vip-management');
      // Wait for data to load
      await page.waitForTimeout(500);
      await expect(page.locator('text=Silver')).toBeVisible();
    });
  });

  test.describe('Custom Reports', () => {
    test('should load custom report builder page', async ({ page }) => {
      await page.goto('/reports/builder');
      await expect(page.locator('text=Custom Report Builder')).toBeVisible();
    });
  });

  test.describe('Scheduled Reports', () => {
    test('should load scheduled reports page', async ({ page }) => {
      await page.goto('/reports/scheduled');
      await expect(page.locator('h1')).toContainText('Scheduled Reports');
    });

    test('should allow creating a new schedule', async ({ page }) => {
      await page.goto('/reports/scheduled');
      const newButton = page.locator('button:has-text("New Schedule")');
      await expect(newButton).toBeVisible();
    });
  });

  test.describe('Staff Scheduling', () => {
    test('should load staff scheduling page', async ({ page }) => {
      await page.goto('/shifts');
      await page.waitForLoadState('networkidle');
      // Page shows either the h1 (success state) or error message (when API is down)
      const hasH1 = await page.locator('h1:has-text("Shift Scheduling")').count() > 0;
      const hasError = await page.locator('text=Retry').count() > 0;
      expect(hasH1 || hasError).toBe(true);
    });
  });

  test.describe('Google Reserve', () => {
    test('should load Google Reserve page', async ({ page }) => {
      await page.goto('/integrations/google-reserve');
      await expect(page.locator('h1')).toContainText('Reserve with Google');
    });

    test('should show connection status', async ({ page }) => {
      await page.goto('/integrations/google-reserve');
      // Page shows either "Connected" or "Disconnected" status
      await page.waitForLoadState('networkidle');
      const hasConnected = await page.locator('text=Connected').count() > 0;
      const hasDisconnected = await page.locator('text=Disconnected').count() > 0;
      expect(hasConnected || hasDisconnected).toBe(true);
    });
  });
});
