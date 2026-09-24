# DataRoom Lens

Diligence associate for one renewable-energy asset. `frontend/` is the React UI; `backend/` will hold the FastAPI service. `design/` is the source of truth for both.

## Frontend rules
- The UI spec is design/DESIGN_HANDOFF.md. The API contract is design/api/types.ts.
- Use only CSS variables from design/tokens.css. No raw hex, no new colours or fonts.
- Styling is Tailwind v4 (frontend/src/styles/app.css). Its theme is mapped from the tokens and every default palette, font, radius, shadow and text size is cleared, so only token utilities exist: `bg-surface`, `text-muted`, `border-hairline`, `rounded-card`, `text-md`, `font-display`... Spacing is the 4px token base (`p-4` = 16px). Shared primitives live in frontend/src/components/ui.tsx (Button, Tag, ResultPill, Kbd, Sk); reuse them rather than re-styling.
- Type roles come from tokens.css classes: `t-display`, `t-title`, `t-label`, `t-ref`.
- Every status shows glyph + word + colour. Never colour alone.
- Exactly one ink pill (primary button) per view.
- Do not add features that are not in the design.
- Native elements first; ARIA only for the findings grid and the pane separator.

## Frontend commands (run in frontend/)
- `npm run dev` then open http://localhost:5173
- `npm test` (vitest, data layer), `npm run typecheck`, `npm run build`
- With the dev server running: `npm run a11y` (axe, light + dark), `node scripts/walkthrough.mjs` (keyboard-only demo loop), `node scripts/shots.mjs <dir>` (1440x900 screenshots)
