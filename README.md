# DataRoom Lens

A diligence associate for one renewable-energy asset (Brackenfield Solar & Storage, synthetic). It shows what is wrong, what is missing and what to ask the seller. Every fact cites a verbatim, code-verified quote, and every reviewer correction becomes a regression test that the eval gate re-checks.

| Folder | What |
|---|---|
| `design/` | UI spec, tokens, API contract (`api/types.ts`) and fixtures. Source of truth. |
| `frontend/` | React + TypeScript + Vite + Tailwind v4 UI, themed from `design/tokens.css`. Runs on fixtures today. |
| `backend/` | FastAPI service (to come). Must return the shapes in `design/api/types.ts`. |

## Run the UI

```bash
cd frontend
npm ci
npm run dev
```

Then open http://localhost:5173. `VITE_USE_FIXTURES=true` (the default) reads `frontend/src/api/fixtures/` and keeps review and eval state in memory. Set it to `false` to call the backend at `/api`, which the dev server proxies to `localhost:8000`.

## Checks

```bash
npm test               # data layer: review loop, undo, eval, RFI markdown
npm run build          # typecheck + production build
npm run a11y           # axe on every view, light and dark (needs the dev server)
node scripts/walkthrough.mjs   # keyboard-only demo loop, asserted step by step
```
