// Produces dist/styles.css = fonts + tokens + base typography + component CSS, and copies fonts to dist/fonts.
import { readFileSync, writeFileSync, mkdirSync, cpSync, existsSync, rmSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');
const read = (p) => readFileSync(join(root, p), 'utf8');

mkdirSync(join(dist, 'fonts'), { recursive: true });
cpSync(join(root, 'src/fonts'), join(dist, 'fonts'), { recursive: true });

const fonts = read('src/styles/fonts.css').replaceAll('url(../fonts/', 'url(./fonts/');
const componentCssPath = join(dist, 'index.css');
const components = existsSync(componentCssPath) ? readFileSync(componentCssPath, 'utf8').replace(/\/\*# sourceMappingURL=.*?\*\//g, '') : '';

const out = [
  '/* cepter-ui - fonts, tokens, typography and component styles */',
  fonts,
  read('src/styles/tokens.css'),
  read('src/styles/base.css'),
  components,
].join('\n');
writeFileSync(join(dist, 'styles.css'), out);
for (const f of ['index.css', 'index.css.map']) rmSync(join(dist, f), { force: true });
console.log(`dist/styles.css written (${(out.length / 1024).toFixed(1)} KB)`);
