// Captures 1440x900 screenshots of each view (light and dark) for design review.
// Usage: node scripts/shots.mjs [outDir] (expects `npm run dev` on :5173)
import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';

const out = process.argv[2] ?? 'screenshots';
const base = process.env.BASE_URL ?? 'http://localhost:5173';
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
for (const scheme of ['light', 'dark']) {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, colorScheme: scheme });
  const go = async (hash, name, prep) => {
    await page.goto(`${base}/${hash}`);
    await page.waitForSelector('[role=row][data-focus], article mark, [data-part=rfi]');
    await page.evaluate(() => document.fonts.ready);
    if (prep) await prep(page);
    await page.screenshot({ path: `${out}/${name}-${scheme}.png` });
  };
  await go('#/summary/F-03', 'summary');
  await go('#/evidence/F-03', 'evidence');
  await go('#/requests', 'requests');
  await go('#/evidence/F-03', 'correct-form', async (p) => {
    await p.keyboard.press('c');
    await p.waitForSelector('textarea');
  });
  await go('#/summary/F-03', 'help', async (p) => {
    await p.keyboard.press('?');
    await p.waitForSelector('dialog[open]');
  });
  await page.close();
}
await browser.close();
console.log(`saved to ${out}`);
