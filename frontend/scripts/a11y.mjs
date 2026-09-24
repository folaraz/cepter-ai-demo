// axe accessibility scan of Summary, Evidence (idle + correct form) and Requests, light and dark.
// Usage: npm run a11y (expects `npm run dev` on :5173, or BASE_URL)
import { chromium } from 'playwright';
import { AxeBuilder } from '@axe-core/playwright';

const base = process.env.BASE_URL ?? 'http://localhost:5173';
const browser = await chromium.launch();
let failures = 0;

for (const scheme of ['light', 'dark']) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: scheme });
  const page = await context.newPage();
  const scan = async (name, hash, prep) => {
    await page.goto(`${base}/${hash}`);
    await page.waitForSelector('[role=row][data-focus], article mark, [data-part=rfi]');
    if (prep) await prep();
    const { violations } = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']).analyze();
    failures += violations.length;
    console.log(`${violations.length ? '✕' : '✓'} ${name} (${scheme}): ${violations.length} violation(s)`);
    for (const v of violations) {
      console.log(`   - ${v.id}: ${v.help}`);
      for (const n of v.nodes.slice(0, 4)) console.log(`       ${n.target.join(' ')}  ${n.failureSummary?.split('\n')[1] ?? ''}`);
    }
  };
  await scan('Summary', '#/summary/F-03');
  await scan('Summary + passed list', '#/summary/F-03', () => page.click('button[aria-controls=passed-list]'));
  await scan('Evidence', '#/evidence/F-03');
  await scan('Evidence, correct form with error', '#/evidence/F-03', async () => {
    await page.keyboard.press('c');
    await page.click('button[type=submit]');
    await page.waitForSelector('[aria-invalid=true]');
  });
  await scan('Evidence, missing evidence', '#/evidence/F-01');
  await scan('Requests', '#/requests');
  await scan('Shortcuts dialog', '#/summary', async () => {
    await page.keyboard.press('?');
    await page.waitForSelector('dialog[open]');
  });
  await context.close();
}
await browser.close();
console.log(failures ? `\n${failures} violation(s)` : '\nNo violations.');
process.exit(failures ? 1 : 0);
