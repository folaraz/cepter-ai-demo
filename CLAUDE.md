# DataRoom Lens

Diligence associate for one renewable-energy asset. `frontend/` is the React UI; `backend/` will hold the FastAPI service. `design/` is the source of truth for both.

## Frontend rules
- The UI spec is design/DESIGN_HANDOFF.md. The API contract is design/api/types.ts, plus design/api/ask.types.ts for Ask. Ask's user-facing messages come verbatim from backend/ask.yaml `messages`; never write your own.
- Use only CSS variables from design/tokens.css. No raw hex, no new colours or fonts.
- Styling is Tailwind v4 (frontend/src/styles/app.css). Its theme is mapped from the tokens and every default palette, font, radius, shadow and text size is cleared, so only token utilities exist: `bg-surface`, `text-muted`, `border-hairline`, `rounded-card`, `text-md`, `font-display`... Spacing is the 4px token base (`p-4` = 16px). Shared primitives live in frontend/src/components/ui.tsx (Button, Tag, ResultPill, Kbd, Sk); reuse them rather than re-styling.
- Type roles come from tokens.css classes: `t-display`, `t-title`, `t-label`, `t-ref`.

## Visual style
The product should look crafted, not templated. These were deliberately removed; don't bring them back:
- Numbered eyebrows ("01. Summary") and UPPERCASE letter-spaced micro-labels. Use sentence-case headings via `<SectionHeading>` (title, optional `<Count>`, one-line description).
- Monospace as decoration. Mono is only for keyboard keys in the shortcuts sheet.
- Gradient glows or blobs. The serif headline carries the page.
- Middots (·) joining unrelated bits of text. Give each piece of information its own place.
- Repeating the same reassurance on every item (e.g. "Exact quote" under every fact). State the norm once; flag only exceptions.
- Filler content (placeholder paragraphs, fake context). Show real data or nothing.
- Keyboard caps inside buttons. Shortcuts live in `title` tooltips and the shortcuts sheet.
- Text characters as icons. Use Lucide via `<Icon>`; icon-only controls use `<IconButton>` with an aria-label.
This deliberately overrides the numbered labels and the Summary glow in design/DESIGN_HANDOFF.md.

## Writing for the reviewer
The people using this are diligence lawyers and associates, not engineers. Deal language is fine (COD, PPA, easement, lease term, RFI, severity). System language is not:
- Never show internal ids: check ids (`cable_route_rights`), paragraph ids (`planning:p1:¶4`), run ids, golden item ids (`corr-002`). Show document titles, page numbers and "Finding 3" instead. The ids stay in the API and in URLs.
- No engineering terms in the UI: say "accuracy check" not "eval", "examples tested" not "golden set", "re-checked on every run" not "regression test", "exact quote" not "verified by the verifier".
- Status words and their icons (Lucide, via `<Icon>` in components/ui.tsx) are defined once in frontend/src/lib/status.ts. Change them there. No typed symbols (✓ ◆ ≠) as icons.
- No shorthand a reader has to decode: "Page 4 of 31", not "31p".
- Errors say what happened and what to do ("Couldn't load the findings. Check your connection, then try again."), never raw HTTP messages.
- The RFI export goes to the seller: no internal references in it.
- Every status shows glyph + word + colour. Never colour alone.
- Exactly one ink pill (primary button) per view.
- Do not add features that are not in the design.
- Native elements first; ARIA only for the findings grid and the pane separator.

## Frontend commands (run in frontend/)
- `npm run dev` then open http://localhost:5173
- `npm test` (vitest: data layer, plus Ask component tests in jsdom), `npm run typecheck`, `npm run build`
- With the dev server running: `npm run a11y` (axe, light + dark), `node scripts/walkthrough.mjs` (keyboard-only demo loop), `node scripts/shots.mjs <dir>` (1440x900 screenshots)
