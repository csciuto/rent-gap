const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

// Every page, checked with axe. Add new pages here: [name, path, selector that appears once it has rendered].
const PAGES = [['Dashboard', '/docs/', '#series-container']];  // served from the repo root locally

for (const [name, path, ready] of PAGES) {
  test(`${name}: no accessibility violations`, async ({ page }) => {
    await page.goto(path);
    await expect(page.locator(ready).first()).toBeVisible();
    // Series labels are drawn in their chart line's color, and switched-off series are faded on purpose;
    // both are left out of the contrast check (an open design question), everything else is checked.
    const all = await new AxeBuilder({ page }).disableRules(['color-contrast']).analyze();
    const contrast = await new AxeBuilder({ page }).withRules(['color-contrast'])
      .exclude('.series-label').exclude('.series-row.inactive').analyze();
    const found = [...all.violations, ...contrast.violations];
    expect(found.map((v) => `${v.id}: ${v.nodes.length} × ${v.nodes[0].target}`)).toEqual([]);
  });
}
