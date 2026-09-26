// Keyboard-only walkthrough of the demo's key moment, asserting each step.
// Usage: node scripts/walkthrough.mjs (expects `npm run dev` on :5173, or BASE_URL)
import { chromium } from 'playwright';
import assert from 'node:assert/strict';

const base = process.env.BASE_URL ?? 'http://localhost:5173';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, acceptDownloads: true });
const step = (msg) => console.log(`✓ ${msg}`);
const focused = () => page.evaluate(() => document.activeElement?.getAttribute('data-focus') ?? document.activeElement?.tagName);
const focusIs = (key) => page.waitForFunction((k) => document.activeElement?.getAttribute('data-focus') === k, key, { timeout: 2000 }).then(() => key);
const text = (sel) => page.locator(sel).first().innerText();

await page.goto(`${base}/#/summary`);
await page.waitForSelector('[role=row][data-focus]');

// Tab into the grid: the roving tabindex puts focus on the selected row.
await page.keyboard.press('Tab'); // skip link
for (let i = 0; i < 40 && (await focused()) !== 'row-F-01'; i++) await page.keyboard.press('Tab');
assert.equal(await focused(), 'row-F-01');
step('Tab reaches the selected grid row');

await page.keyboard.press('j');
await page.keyboard.press('ArrowDown');
assert.equal(await focusIs('row-F-03'), 'row-F-03', 'focus follows selection');
assert.equal(await page.getAttribute('[data-focus="row-F-03"]', 'aria-selected'), 'true');
step('J / ↓ move selection and focus to F-03');

await page.keyboard.press('Enter');
await page.waitForSelector('article mark');
assert.match(await text('nav[aria-label=Breadcrumb] [aria-current=page]'), /Evidence · Finding 3/);
assert.match(await text('[data-part=source-toolbar]'), /Source 1 of 3/);
step('Enter opens Evidence at source 1');

// Step through sources with the toolbar button.
await page.getByRole('button', { name: 'Next source' }).focus();
await page.keyboard.press('Enter');
assert.match(await text('[data-part=source-toolbar]'), /Source 2 of 3/);
assert.match(await text('article mark'), /^49\.9 MW$/);
step('Next source swaps the page and highlights the verbatim quote');

// Separator resizes by 20px.
await page.locator('[role=separator]').focus();
await page.keyboard.press('ArrowRight');
assert.equal(await page.getAttribute('[role=separator]', 'aria-valuenow'), '520');
step('Separator ← / → resizes the panes');

// Correct F-03: empty reason is refused, then saved.
await page.locator('body').focus();
await page.evaluate(() => (document.activeElement)?.blur());
await page.keyboard.press('c');
await page.waitForSelector('select');
assert.equal(await focusIs('review-select'), 'review-select');
await page.keyboard.press('Tab');
await page.keyboard.press('Control+Enter');
assert.equal(await page.getAttribute('textarea', 'aria-invalid'), 'true');
assert.match(await text('[data-part=reason-error]'), /Add a short reason so your team knows why\./);
step('Saving without a reason shows the error and keeps focus in the field');

await page.keyboard.type('Planning limit (49.9 MW) and grid export limit (45 MW) are different properties. This is a capacity mismatch: fail, not conflict.');
await page.keyboard.press('Control+Enter');
await page.waitForSelector('[data-part=toast]');
assert.match(await text('[data-part=toast]'), /Correction saved\. We'll re-check it on every run\./);
assert.match(await text('[data-part=finding-status]'), /Corrected/);
assert.match(await text('[data-part=finding-status]'), /Issue found/);
assert.match(await text('[data-part=eval-gate]'), /Re-check needed/);
assert.match(await text('[data-part=eval-gate]'), /1 of 2 re-checked/);
assert.match(await text('[data-part=eval-gate]'), /Examples tested\s+21/);
step('Correct → toast, finding Corrected + Issue found, Re-check needed, 1 of 2 re-checked, 21 examples');

// Undo restores everything and returns focus.
await page.getByRole('button', { name: 'Undo' }).click();
await page.waitForFunction(() => document.querySelector('[data-part=toast]')?.textContent?.includes('Undone'));
assert.match(await text('[data-part=finding-status]'), /Needs review/);
assert.match(await text('[data-part=eval-gate]'), /Up to date/);
assert.match(await text('[data-part=eval-gate]'), /Examples tested\s+20/);
assert.equal(await focusIs('review-accept'), 'review-accept');
step('Undo restores the finding and the accuracy check, focus returns to the review buttons');

// Redo the correction via the buttons, then run the eval.
await page.keyboard.press('c');
await page.waitForSelector('select');
await page.selectOption('select', 'fail');
await page.fill('textarea', 'Capacity mismatch: fail, not conflict.');
await page.getByRole('button', { name: 'Save correction' }).click();
await page.waitForFunction(() => document.querySelector('[data-part=toast]')?.textContent?.includes('Correction saved'));
await page.getByRole('button', { name: 'Re-check now' }).focus();
await page.keyboard.press('Enter');
assert.match(await text('[data-part=eval-gate]'), /Checking…/);
assert.match(await text('[data-focus=run-eval]'), /Re-checking…/);
await page.waitForFunction(() => document.querySelector('[data-part=eval-gate]')?.textContent?.includes('Up to date'), null, { timeout: 5000 });
assert.match(await text('[data-part=eval-gate]'), /2 of 2 hold/);
assert.match(await text('[data-part=toast]'), /Re-check complete\. All your corrections still hold\./);
step('Re-check now: Checking… then Up to date, 2 of 2 corrections hold, toast');

// Summary reflects the correction.
await page.getByRole('button', { name: /Summary/ }).first().click();
const row = page.locator('[data-focus="row-F-03"]');
assert.match(await row.innerText(), /Corrected/);
assert.match(await row.innerText(), /Issue found/);
step('Summary row shows ✎ Corrected and ✕ Issue found');

// Accept from the grid with A.
await row.focus();
await page.keyboard.press('k');
await page.keyboard.press('a');
await page.waitForFunction(() => document.querySelector('[data-part=toast]')?.textContent?.includes('Finding 2 confirmed'));
assert.match(await page.locator('[data-focus="row-F-02"]').innerText(), /Confirmed/);
step('A accepts the selected finding with a toast');

// Export RFIs.
await page.getByRole('button', { name: /Seller questions/ }).click();
const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', { name: 'Download questions' }).click()]);
assert.equal(download.suggestedFilename(), 'brackenfield-rfis.md');
assert.match(await text('[data-part=toast]'), /Downloaded 3 seller questions/);
step('Download questions saves brackenfield-rfis.md and toasts');

// Shortcuts dialog: ? opens, Esc closes, focus returns.
await page.getByRole('button', { name: 'Keyboard shortcuts' }).focus();
await page.keyboard.press('Enter');
await page.waitForSelector('dialog[open]');
await page.keyboard.press('Escape');
await page.waitForSelector('dialog:not([open])', { state: 'attached' });
assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('aria-label')), 'Keyboard shortcuts');
step('Shortcuts dialog opens, Esc closes, focus returns to the opener');

// Ask: "/" opens Ask, a suggested question answers, a citation opens its passage beside it.
await page.locator('body').focus();
await page.evaluate(() => (document.activeElement)?.blur());
await page.keyboard.press('/');
await page.waitForFunction(() => document.activeElement?.id === 'ask-input');
await page.keyboard.type('Do the documents agree on the export capacity?');
await page.keyboard.press('Enter');
await page.locator('article', { hasText: 'Searching the documents…' }).waitFor();
await page.getByText('Every sentence is backed', { exact: false }).first().waitFor({ timeout: 6000 });
assert.equal(await page.evaluate(() => document.activeElement?.id), 'ask-input', 'focus stays in the Ask input');
const chip = page.getByRole('button', { name: 'Open source: Grid connection offer, page 2' });
await chip.focus();
await page.keyboard.press('Enter');
assert.equal(await chip.getAttribute('aria-pressed'), 'true');
assert.match(await text('article mark'), /Maximum Export Capacity at the Point of Connection shall be 45 MW/);
step('"/" opens Ask; a question answers with chips; a citation opens its highlighted passage');

// Shortcuts do not fire while typing.
await page.getByRole('button', { name: /Evidence/ }).first().click();
await page.keyboard.press('r');
await page.waitForSelector('textarea');
await page.keyboard.type('jkac?');
assert.equal(await page.inputValue('textarea'), 'jkac?');
assert.equal(await page.locator('dialog[open]').count(), 0);
step('Single-key shortcuts never fire inside a field');

await browser.close();
console.log('\nWalkthrough passed.');
