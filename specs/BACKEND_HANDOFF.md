# Backend handoff

Start here for the backend session. The frontend is done and runs on fixtures; this file lists what the backend needs to know that isn't in the spec.

## Where things are

| Path | Status |
|---|---|
| `backend/dataroom-lens-complete/` | **Canonical bundle.** Spec, schema, ontology, checks, `ask.yaml`, tools, data room, golden sets, backend prompts. Its `HANDOFF.md` says to unzip at repo root. |
| `backend/dataroom-lens-backend-bundle/` | Older, incomplete copy (no Ask). Delete once the complete bundle is in place. |
| `backend/SPEC.md` | Loose copy of the complete bundle's spec (identical apart from a trailing newline). Delete it. |
| `design/` | **Keep the repo's version, do not overwrite from the bundle.** It is ahead of the bundle's `design/` (see "Fixture wording" below). `design/api/types.ts` and `design/api/ask.types.ts` are the contract and match the bundle. |
| `frontend/` | Done. Read-only for the backend work except `frontend/src/api/client.ts` at step 13. |

Suggested first move: lay the complete bundle's `backend/`, `data/`, `evals/` into the repo root (not its `design/`), delete both bundle folders and the loose `SPEC.md`, then follow `backend/CLAUDE_CODE_PROMPTS.md` from step 0.

## Frontend facts the backend must honour

- Contract: every endpoint in `design/api/types.ts` and `design/api/ask.types.ts`, under `/api`. The dev server proxies `/api` to `http://localhost:8000`.
- Switch: `frontend/.env` → `VITE_USE_FIXTURES=false` makes `client.ts` call the API instead of fixtures. Nothing else in the UI changes.
- `POST /api/evals/run` may return `state: "running"`; the client polls `GET /api/evals/latest` every 750 ms until it isn't.
- `GET /api/rfi.md` is downloaded as-is and sent to the seller. It must contain **no internal ids** (no check ids, no "Blocks check" line). Fixture-mode output: `frontend/src/api/markdown.ts`.
- Error bodies are never shown to users; the UI shows its own messages. Status codes matter (400 for Ask validation).
- The UI never displays check ids, paragraph ids, run ids or golden item ids. They must still be in the API (URLs, citations, React keys).

## Fixture wording differs from the bundle (decide once)

The frontend was rewritten for non-technical reviewers (lawyers). Two things now differ from what the bundle's templates will produce:

1. **Finding `how` text.** `design/api/fixtures/findings/F-0*.json` has plain-English `how` and missing-evidence `note` strings. The bundle's `backend/checks/*.yaml` (`how:` templates) and `backend/tests/contract/expected/findings/*.json` still have the old technical text, so `check_templates.py` and the contract tests encode the old wording.
   Recommended: update the check templates and `tests/contract/expected/` to the repo's `design/api/fixtures/findings/` text, then re-run `check_templates.py`.
2. **Ask template sentence.** `backend/ask.yaml` → `graph_queries.cable_route_rights`: "…so rights over them are missing evidence, raised as {rfi_id}." Shown to users as-is. Optional: plainer wording (e.g. "…so the project has no confirmed rights over them; raised as {rfi_id}.") — change `ask.yaml`, the Ask fixture `r01.json` (both copies), and whatever `check_ask.py` compares.

Already aligned (no action): `summary.json` page counts, "Fenland Distribution Networks", and the second missing document (Condition 5) were taken from the bundle.

## Small contract mismatch

`design/api/fixtures/ask/unavailable.json` has `"question": null`; `AskResponse.question` is typed `string`. The backend should return the asked question (the UI fills it in for fixtures).

## Frontend checks to run at step 13 (API switched on)

From `frontend/`, with `npm run dev` running and the API on :8000:

```bash
npm test                        # vitest: client + Ask component tests (fixture mode)
node scripts/walkthrough.mjs    # keyboard-only demo loop incl. correct → re-check → Ask
npm run a11y                    # axe, all views, light + dark
```

`walkthrough.mjs` asserts user-facing text (e.g. "Correction saved…", "Up to date", "1 of 2 re-checked", "Examples tested 21"), so it doubles as a check that the API produces the same states as the fixtures.

## Repo state at handoff

Last commit: `2da13bf`. Everything since (Tailwind, copy rewrite, redesign, Ask, sidebar) is **staged, not committed**. Commit it before starting the backend so the two streams don't mix.
