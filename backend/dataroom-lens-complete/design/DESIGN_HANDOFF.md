# DataRoom Lens: UI design handoff

This folder is the source of truth for the frontend. Build the UI to match it exactly. If something here is ambiguous, match the artboard; if the artboard is silent, choose the simplest option and note it in the PR.

**Live design (clickable, press Play):** https://claude.ai/artifact/QTUuik1ByprR9MvFnF5gvc

## What is in this folder

| Path | What it is |
|---|---|
| `DESIGN_HANDOFF.md` | This spec. |
| `CLAUDE_CODE_PROMPTS.md` | The build, split into small tasks, in order. |
| `tokens.css` | Every colour, font, radius and size as CSS variables, light and dark. |
| `api/types.ts` | The API contract. The UI and the FastAPI backend both follow it. |
| `api/ask.types.ts` | The Ask contract (added with the Ask feature). Reuses `QuoteEvidence` from `types.ts`. |
| `api/fixtures/` | Realistic data in exactly those shapes, so the UI can be built before the backend exists. Identical to `backend/tests/contract/expected/`, so fixture mode and the real API return the same data. |
| `api/fixtures/ask/` | Ask responses for the five suggested questions, an unavailable response, and a test-only answer with a dropped sentence. Every quote and offset is taken from the real data room text. |
| `artboards/*.dc.html` | Design source files. Read them for exact spacing, copy and structure. They need the design tool's runtime to render, so use the live link above to see them. |

Artboards: `workspace` (the app, all three views, interactive), `states` (loading, rejected by verifier, conflict, missing evidence, partial, error), `corrections` (the corrections-become-tests story for the README), `tokens` (the visual system).

## Stack for the UI

React + TypeScript + Vite, in `frontend/`. Plain CSS modules or a single CSS file using the variables in `tokens.css`; no component library is needed. Import `tokens.css` once in `main.tsx`. No raw hex values in components. Use native elements first (`button`, `select`, `textarea`, `dialog`); add ARIA only where native elements cannot express the pattern (the findings grid, the separator).

## The product in one paragraph

A diligence associate for one renewable-energy asset. It shows what is wrong, what is missing and what to ask the seller. Every fact and finding cites a verbatim quote that code has verified. A reviewer can accept, reject or correct any finding, and every reject or correct becomes a regression test in the golden set, which the eval gate re-checks. Reviewers can also ask questions about the data room: every answer sentence cites a verified quote, and when the documents don't answer, Ask says so instead of guessing (see "View 4: Ask").

## Layout (1440 × 900 reference)

```
┌──────────────────────────────── top bar 56px ─────────────────────────────────┐
│ ● DataRoom Lens   Brackenfield Solar & Storage / {view}   ◇ Synthetic · [?]   │
├───────────── sidebar 248px ─────┬────────────── main (scrolls) ───────────────┤
│ Asset name + subtitle           │                                             │
│ 01. Summary        5            │   Summary | Evidence | Requests view        │
│ 02. Evidence       F-03         │                                             │
│ 03. Requests       3            │                                             │
│ Documents · 5                   │                                             │
│  ● cited  · not cited           │                                             │
│ ○ Cable route easement (missing)│                                             │
│ ── Eval gate ✓ Passing          │                                             │
│ Golden set / corrections / cost │                                             │
│ [Run eval]                      │                                             │
└─────────────────────────────────┴─────────────────────────────────────────────┘
```

Sidebar background `--canvas-soft`, 1px `--hairline` right border. Nav items are 36px pills; the active one is a `--surface` pill with a 1px hairline ring and `aria-current="page"`. In the documents list, documents cited by the currently selected finding get a filled dot and ink text.

## View 1: Summary (default)

Top to bottom, 32px/40px page padding, 28px between sections:

1. **Headline block.** Label `01. Diligence summary`, then `summary.headline` in `.t-display`. Right-aligned meta: `8 checks · run r-0921-a · 21 Sep 14:02`. One soft glow sits behind the headline only: `radial-gradient(closest-side, var(--orb), var(--orb-0))`, about 620×300px, absolutely positioned, `aria-hidden`, `pointer-events: none`. It must not sit behind any card.
2. **Asset facts** card. A 4×2 grid of buttons, hairlines between cells. Each cell: label (12px muted), value (15px, 500), quote status tag. Clicking opens that fact's finding in Evidence.
3. **Critical dates** card. A horizontal axis spanning `date_window`; each `DateMark` is a dot + stem + button label (date 13px 600, label 11px). Tone `clash` uses `--critical`, `warning` uses `--conflict`. Draw a translucent `--critical` band between the clash dates and a clash label below it. Year ticks along the bottom in DM Mono. Below the axis, a full-width button row with the `long_horizon` note and its flag. Place labels in three rows (above-far, above-near, below-near) so none overlap; see the artboard for exact positions.
4. **Findings** grid (the hero). See "Findings grid" below.

## Findings grid

A `--surface` card, radius 16, hairline outline. `role="grid"`, `aria-label="Findings"`, `aria-rowcount`. Header row uses `.t-label`; the Severity header has `aria-sort="descending"`.

Columns: `#` 34px · Finding (flex) · Severity 96px · Result 158px · Evidence 136px · Review 144px.

- **Finding cell:** title 14px 500, and underneath in 12px muted: `check_id` (DM Mono) · source document titles, truncated with an ellipsis.
- **Severity:** tag, glyph + word in the severity colour.
- **Result:** a pill badge: 24px high, 1px border in the result colour, 8% tint of that colour, glyph + word.
- **Evidence:** `3 verified quotes · 1 gap` (derived from `quote_count`, `gap_count`).
- **Review:** tag, glyph + word.
- **Row:** min-height 44px, hairline top border, hover `--surface-strong`. Selected: `--surface-strong` with a 2px inset ink bar on the left, `aria-selected="true"`.
- **Roving tabindex:** only the selected row has `tabIndex=0`; the rest `-1`. When selection moves by keyboard, **move focus to the new row** (the design prototype does not do this yet; the build must).
- After the five rows, a full-width button: `✓ 3 checks passed · show/hide` that expands the passed list.

## View 2: Evidence (split pane)

Left panel (default 500px, resizable 400–760) on `--surface`; right side on `--canvas`.

**Left, scrolling:** `← Summary` link and J/K pill buttons; label `{num}. {check_id}`; title in `.t-title`; severity tag, result pill, review tag; "Why it matters" (14px); "How the check decided" (13px, `--body`); "Evidence · N items" as a list of source cards (radius 12, 1px border; the selected one has an ink border) showing document title, quote status tag, `paragraph_id · role`. Missing evidence renders as a dashed `--missing` card with `--missing-soft` fill.

**Left, pinned footer:** label "Your review" and the hint "Corrections are saved as regression tests". Idle: three equal pills, **Accept** (ink pill, the only one in this view), Reject, Correct, each showing its key. Correct/Reject replace the buttons with a form: for Correct, a `select` of results (44px, radius 8); for both, a required reason `textarea` with `aria-invalid` and an error message when empty ("Add a reason. It becomes the test's description."); Cancel + **Save to golden set** (ink pill).

**Separator:** 9px, `role="separator"`, `aria-orientation="vertical"`, `aria-valuemin/max/now`, `tabIndex=0`; ←/→ resize by 20px. Pointer drag too.

**Right:** a toolbar with file name, paragraph ID, `Source i of n`, Previous / Next source pills. Below, the document page: white sheet (always white, even in dark mode, like paper), 1px hairline, radius 4, `--shadow`, padding 56×64. Header row in DM Mono uppercase (document title, page). A context paragraph in muted, the clause heading in Newsreader 300 19px, the cited paragraph with `paragraph_text[quote_start:quote_end]` wrapped in `<mark>` (`--mark`), another context paragraph, and a footer line explaining the quote status ("Verified quote. Quote found verbatim in this paragraph by the verifier. Not model-asserted.").

Selecting a source card, or Previous/Next, swaps the page. Opening a finding always starts at source 1.

## View 3: Requests

Label `03. Requests for information`, headline "Three questions for the seller, each tied to the check it unblocks." in `.t-display`, a one-line explanation, and **Export Markdown** (the ink pill for this view) on the right. Then a single card with one row per RFI: DM Mono ID column, title + severity tag + "View finding →" link, request (14px, max ~680px), and a small definition list: Why · Documents · Unblocks (check id in DM Mono). Export downloads `GET /api/rfi.md` (fixture mode: build the Markdown client-side from `rfi.json`) and shows a toast.

## View 4: Ask

Added after the original artboards, so there is no artboard for it: design it inside the current UI's patterns (navigation, headings, cards, chips, tokens). Contract: `api/ask.types.ts`. Behaviour: `backend/SPEC.md` C14. User-facing messages: `backend/ask.yaml` → `messages` (use those strings exactly).

**What it does.** A reviewer asks a question about the data room. The backend answers one of three ways: **lookup** (a single fact: retrieved paragraphs, a model-drafted answer, every sentence verified against its quotes before it is sent); **relationship** (a fixed query over the asset model, rendered from templates; a sentence stating an absence carries `finding_id` instead of a citation); or **abstained** (the documents don't answer it, or it is off-topic). Answers are **not streamed**: they arrive whole after about 2–4 s because they are verified first. The five suggested questions always work. A free-form question returns `status: "unavailable"` unless live Ask is switched on at the server.

**Behaviour.**
1. **Input:** a labelled textarea, 3–500 characters, inline error outside that range (`aria-invalid` plus message, cleared on edit). Enter submits, Shift+Enter adds a line. **Ask** is this view's one ink pill.
2. **Suggestions** from `GET /api/ask/suggestions`: shown before the first question and after an unavailable response, as buttons that submit immediately.
3. **Pending:** keep the question visible, disable submit, show a quiet status in an `aria-live="polite"` region ("Searching the documents…", then "Checking every quote…" after about 1 s). Cancellable (AbortController).
4. **Answered:** sentences as one readable paragraph, each followed by its citation chips (document short title + paragraph ID in DM Mono). A chip opens the Evidence view on that `QuoteEvidence`, quote highlighted, exactly like a finding's source. A sentence with `finding_id` gets a finding chip that opens the finding. A meta line gives the route in plain words ("Looked up in the documents" / "From the asset model"), latency, and "Replayed" / "Cached" / "Live" from `mode`. A verified marker in the status vocabulary: "✓ Every sentence cites a verified quote". If `dropped_sentences > 0`, a quiet note: "1 sentence was removed because its quote couldn't be verified." (pluralised). If `related_finding_id` / `related_rfi_id` are set, a "Related" line linking to them.
5. **Abstained:** a designed state, never styled as an error: the `message`, related links if any, and a link to Requests ("Ask the seller instead").
6. **Unavailable:** the `message` and the suggestions.
7. **Errors** (network, 5xx, 400): scoped inline error with Retry; the question stays in the input.
8. **History:** this session's questions and answers in memory, newest first, each keeping its own state.
9. **Keyboard:** one shortcut to focus the Ask input, added to the table below and the shortcuts dialog. After an answer arrives, keep focus in the input and announce the result through the live region.
10. **Accessibility:** citation chips are real buttons with labels like "Open source: Grid connection offer, paragraph grid_offer:p2:¶3".

## Overlays

- **Toast:** bottom centre, ink pill (`--primary` / `--on-primary`), 48px, `role="status"` `aria-live="polite"`. Text + outline-pill **Undo** (when undoable) + ×. Auto-dismiss after 8s; Undo restores the previous state and returns focus to the affected row or button.
- **Shortcuts dialog:** opened by `?` or the top-bar button. Native `<dialog>` with `showModal()`, radius 16, `--shadow`, focus trapped, Esc closes, focus returns to the opener.

## Keyboard

| Key | Where | Action |
|---|---|---|
| J / ↓, K / ↑ | findings grid, Evidence | next / previous finding |
| Enter | findings grid | open Evidence for selected finding |
| A | grid or Evidence | accept (toast with Undo) |
| C | grid or Evidence | open Correct form |
| R | Evidence | open Reject form |
| ← / → | separator focused | resize panes |
| ? | anywhere | shortcuts dialog |
| Esc | dialog, form | close / cancel |

Single-key shortcuts never fire while focus is in an input, select or textarea.

## Status vocabulary (use exactly these)

| Axis | Values (glyph, word, colour token) |
|---|---|
| Severity | ◆ Critical `--critical` · ▲ High `--high` · ● Medium `--medium` · ○ Low `--low` |
| Result | ✕ Fail `--critical` · ≠ Conflict `--conflict` · ○ Missing evidence `--missing` · ✓ Pass `--ok` |
| Review | ◇ AI-extracted `--body` · ! Needs review `--high` · ✓ Lawyer-verified `--ok` · ✎ Corrected `--missing` · ✕ Rejected `--muted` |
| Quote | ✓ Verified quote `--ok` · ✓✓ Corroborated `--ok` · ≠ Conflicting value `--conflict` |

Glyphs are `aria-hidden`; the word carries the meaning. Never colour alone.

## Review loop behaviour (the demo's key moment)

1. Reviewer opens F-03 (conflict), presses Correct, picks Fail, writes the reason, saves.
2. `POST /api/findings/F-03/review` returns the updated row, `golden_item_id: "corr-002"` and eval `state: "stale"`.
3. Toast: "Saved as corr-002 in the golden set" with Undo. Row review becomes ✎ Corrected; result becomes ✕ Fail.
4. Sidebar eval tag becomes `! Re-run needed`; corrections read `1 of 2 checked`; golden set 21.
5. Run eval: button reads "Running eval…", tag `◌ Running…`, then `✓ Passing` and corrections `2 of 2`, with toast "Eval passed · 96% · all corrections still hold".

In fixture mode, simulate steps 2 and 5 in the data layer (about 1s for the eval run).

## Data layer

`frontend/src/api/client.ts` exposes `getSummary`, `getFinding`, `postReview`, `undoReview`, `getRfi`, `getRfiMarkdown`, `runEval`, `getEvalLatest`, `askQuestion(question, signal)` and `getAskSuggestions`. A single flag `VITE_USE_FIXTURES=true` makes them read from `design/api/fixtures/` (copied or imported into `frontend/src/api/fixtures/`) and keep review/eval state in memory. When the backend exists, set it to false and the same functions call FastAPI. Types come from `api/types.ts` and `api/ask.types.ts` until the backend's OpenAPI schema exists.

Ask in fixture mode: suggestions from `fixtures/ask/suggestions.json`; the five suggested questions return `fixtures/ask/{id}.json`; any other question returns `fixtures/ask/unavailable.json` (mirroring the server default, live Ask off); resolve after about 1.5 s so the pending state is visible. `fixtures/ask/test-dropped.json` is for tests only.

## States every view needs

- **Loading:** skeleton rows with the real row height and column widths (see `states` artboard); nothing shifts when data arrives.
- **Error:** scoped message with Retry, in the interface's voice ("Couldn't load findings. Retry."), never a blank screen.
- **Empty:** not expected for the demo; if `findings` is empty, show "All 8 checks passed" with the passed list.

## Accessibility checklist

- Skip link to `#main`; landmarks: `header`, `nav` (sidebar, labelled), `main`.
- One `h1` per view; section headings in order.
- Contrast: use only token colours; they are pre-checked. Do not introduce new greys.
- 2px `--focus` ring on every interactive element, including grid rows and the separator.
- Targets at least 24×24px (buttons are 32–36px high).
- `prefers-reduced-motion` respected (handled in `tokens.css`).
- Works at 200% zoom: the sidebar may collapse; no content lost.

## Do not

- Add features beyond this spec (command palette, chat threads, regenerate or thumbs on answers, charts, extra filters). Ask is in scope as specified above; nothing more.
- Stream answers or animate them in word by word, or show an answer sentence without its citations or finding link.
- Use gradients anywhere except the one Summary glow.
- Use more than one ink pill per view.
- Show any value that has no verified quote.
- Use the ElevenLabs name, logo or fonts; the look is inspired by editorial principles only.

## Definition of done

1. Summary, Evidence and Requests match the live artboard side by side at 1440×900.
2. The full review loop above works with fixtures, including Undo.
3. Keyboard-only walkthrough: open a finding, step through sources, correct it, run eval, export RFIs, ask a suggested question and open one of its citations.
4. Every Ask state renders: suggestions, pending (with cancel), answered (with a finding chip and the dropped-sentence note), abstained, unavailable, error.
5. axe (or Lighthouse accessibility) reports no violations on each view, including Ask.
6. Light and dark both correct (toggle via `data-theme` on `<html>`).
