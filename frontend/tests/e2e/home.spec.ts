import { test, expect } from '@playwright/test';

test('home page has navigation', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Enterprise RAG Platform')).toBeVisible();
  await expect(page.getByText('Chat Console')).toBeVisible();
});
