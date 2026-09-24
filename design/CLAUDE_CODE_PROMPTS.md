# Claude Code prompts for tonight

Run these in order, one per task, from the repo root. After each one: run the app, compare with the live design (https://claude.ai/artifact/QTUuik1ByprR9MvFnF5gvc), commit. Rough times assume things go smoothly; if you fall behind, stop after prompt 6 and keep the rest for Sunday.

## 0. Add the rules to CLAUDE.md (2 min, do it yourself)

Paste this into the repo's `CLAUDE.md`:

```
## Frontend rules
- The UI spec is design/DESIGN_HANDOFF.md. The API contract is design/api/types.ts.
- Use only CSS variables from design/tokens.css. No raw hex, no new colours or fonts.
- Every status shows glyph + word + colour. Never colour alone.
- Exactly one ink pill (primary button) per view.
- Do not add features that are not in the design.
- Native elements first; ARIA only for the findings grid and the pane separator.
```

## 1. Scaffold (15 min)

```
Read design/DESIGN_HANDOFF.md and design/api/types.ts. Create frontend/ with Vite +
React + TypeScript. Import design/tokens.css once in main.tsx. Copy design/api/types.ts
to frontend/src/api/types.ts and design/api/fixtures/ to frontend/src/api/fixtures/.
Create frontend/src/api/client.ts with getSummary, getFinding, postReview, undoReview,
getRfi, getRfiMarkdown, runEval and getEvalLatest, switched by VITE_USE_FIXTURES
(default true) as described in the "Data layer" section. In fixture mode keep review
and eval state in memory and simulate the eval run with a ~1s delay. Add a vitest test
that postReview with action "correct" returns a golden_item_id and eval state "stale",
and that runEval returns to "passing". Don't build any UI yet beyond an empty App.
```

## 2. App shell (30 min)

```
Build the app shell from design/DESIGN_HANDOFF.md ("Layout") and
design/artboards/workspace.dc.html: skip link, 56px top bar, 248px sidebar with the
asset block, the three numbered nav pills, the documents list (cited documents
highlighted for the selected finding), the missing-document button, and the eval gate
block with Run eval. Keep selected view and selected finding in one small store
(React context + useReducer is enough). Wire Run eval to the client and show the
running/passing states. No view content yet.
```

## 3. Summary view (60 min)

```
Build the Summary view exactly as specified in DESIGN_HANDOFF.md ("View 1: Summary"),
reading getSummary(): headline block with the single glow, the asset facts grid, the
critical dates timeline (position marks by date within date_window; labels in the three
rows shown in the artboard so none overlap; clash band and label; long-horizon row), and
the findings grid ("Findings grid"): role="grid", roving tabindex with focus following
selection, J/K/arrows/Enter/A/C, passed-checks toggle. Clicking a fact, a date or a row
selects the finding; Enter or double-click opens Evidence. Add the loading skeleton and
the error state.
```

## 4. Evidence view (60 min)

```
Build the Evidence view from DESIGN_HANDOFF.md ("View 2: Evidence"), reading
getFinding(id). Left panel with finding header, why, how, evidence cards (quote and
missing kinds), pinned review footer. Keyboard-resizable separator (role="separator",
aria-valuenow, ←/→ by 20px, pointer drag, clamp 400–760). Right side: toolbar with
source stepper and the white document page, highlighting
paragraph_text.slice(quote_start, quote_end) in a <mark>. J/K move between findings;
opening a finding starts at source 1.
```

## 5. Review loop + toast (45 min)

```
Implement "Review loop behaviour" from DESIGN_HANDOFF.md. Accept, Reject and Correct
call postReview; Reject and Correct need a non-empty reason (aria-invalid plus the
error text from the spec). Correct includes a select of results. On success update the
row, the sidebar eval block and the golden set count. Add the toast (role="status",
8s auto-dismiss, Undo calls undoReview and returns focus to the affected row). Add a
test for the full correct -> stale -> run eval -> passing sequence.
```

## 6. Requests view (25 min)

```
Build the Requests view from DESIGN_HANDOFF.md ("View 3: Requests") reading getRfi().
Export Markdown downloads getRfiMarkdown() (in fixture mode, generate the Markdown
from rfi.json: one "### RFI-01: title (Severity)" block per request with Request, Why,
Documents expected, Blocks check). Show a toast after export.
```

## 7. Shortcuts dialog + dark mode (20 min)

```
Add the shortcuts dialog (native <dialog>, showModal, Esc closes, focus returns to the
opener) opened by ? and the top-bar button, listing the table in "Keyboard". Add a
theme toggle that sets data-theme on <html>, defaulting to the system preference.
Single-key shortcuts must not fire inside inputs, selects or textareas.
```

## 8. Accessibility and fidelity pass (20 min)

```
Run @axe-core/react (or Playwright + axe) on Summary, Evidence and Requests in light and
dark, and fix every violation. Then compare each view with
design/artboards/workspace.dc.html and list every difference in spacing, size, colour
or copy; fix them. Finally do a keyboard-only walkthrough (open a finding, step
through sources, correct it, run eval, export RFIs) and fix anything that loses focus.
```

## Tomorrow, when the backend exists

```
Set VITE_USE_FIXTURES=false. Generate types from the FastAPI OpenAPI schema with
openapi-typescript into frontend/src/api/schema.ts and make client.ts use them. Report
any field that differs from design/api/types.ts, and fix the backend or the client so
the fixtures and the real API return identical shapes.
```
