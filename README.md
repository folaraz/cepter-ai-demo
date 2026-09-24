# cepter-ai-demo

`cepter-ui` is an editorial voice-AI React design system built from [design-system/design-system.md](design-system/design-system.md). It's synced to Claude Design with `/design-sync`.

```bash
npm ci
npm run build          # dist/index.js, dist/index.d.ts, dist/styles.css, dist/fonts/
npm run storybook      # http://localhost:6006
```

```jsx
import { Page, HeroBand, Button } from 'cepter-ui';
import 'cepter-ui/styles.css';
```

For the token and component vocabulary, see [.design-sync/conventions.md](.design-sync/conventions.md).
