# Session handoff: backend built, recording in progress

Written 2026-09-28 at the end of the session that built the backend. Start here in a new
session, then read `CLAUDE.md`, `specs/SPEC.md` and `backend/README.md`.

## Where things stand

Every backend component in `specs/SPEC.md` (C0–C14) is built, tested and merged to
`main` (PRs #1–#17, each with green CI). Locally: 279 tests pass, 4 skip (the
recorded-model tests skip until recordings match), and ruff, mypy and the three bundle
checks are green.

| Component | What it is | PR |
|---|---|---|
| C0 | FastAPI skeleton, config, `lens migrate`, compose, CI, pre-commit | #1 |
| C1 | PDF ingestion (`lens ingest`), identical to `tools/check_dataroom.py` | #2 |
| C2 | Repositories (`app/db/repositories/`), one per table group | #3 |
| C3 | LLM adapter with record/replay/live/replay_first and `llm_calls` tracing | #4 |
| C4 | Extraction pass 1 (`lens record`, `lens run`) | #5 |
| C5 | Verifier pass 2 | #6 |
| C6 | Consolidation pass 3 (merging, property groups, provenance) | #7 |
| C7 | Check playbook (8 checks, findings) | #8 |
| C8 | Summary, RFIs, read API, `lens seed` | #9 |
| C9 | Reviews, sessions, undo, `lens golden export` | #10 |
| C10 | Serves `frontend/dist`; `tests/test_api_types.py` holds models to `types.ts` | #11 |
| C11 | Accuracy check (`lens eval`), eval endpoints | #12 |
| C12 | Dockerfile, `railway.json`, `lens release`, JSON logs | #13 |
| C13 | Retrieval index (`lens index`), hybrid search, `lens ask calibrate` | #14 |
| C14 | Ask (`POST /api/ask`, suggestions), `lens record --ask` | #15 |
| — | Decisions: per-item gate, nullable clash/long-horizon, RFI empty state | #16 |
| — | Fixes from the first real-model recording (`extract.v2`) | #17 |

## Recordings: done

`backend/fixtures/llm/` holds 28 committed recordings: 5 × `extract.v3`, 15 ×
`ask.route.v2`, 8 × `ask.answer.v1`. `lens eval` scores 1.000 (PASSING): every golden
item passes, citation validity 100%, 0 verifier rejections, routing 13/15 (reported
only). The recorded-model tests run and pass (283 passed, none skipped).

`extract.v3` makes every Party carry a quoted name in every document and cite the
paragraph that names it in its role. `ask.route.v2` sends single-value questions to
lookup even when a graph query covers the value. Re-record whenever a prompt version
changes; delete the old version's files so none are orphaned.

## After recordings: remaining steps

1. **Step 13, switch the UI to the real API** (`specs/CLAUDE_CODE_PROMPTS.md` §13):
   - Copy `backend/tests/contract/expected/summary.json` and `findings/*.json` over
     `frontend/src/api/fixtures/` and `design/api/fixtures/`. The user decided to **keep
     the technical `how` text** from the check templates; the UI fixtures still carry an
     older plain-English `how`. One source of wording: the templates.
   - `VITE_USE_FIXTURES=false`; generate `frontend/src/api/schema.ts` with
     openapi-typescript and report field differences.
   - Walk the demo in the browser against the API: Summary, open F-03, step through
     sources, correct it, run the accuracy check, undo, download RFIs, each suggested
     Ask question. Compare with fixture mode. Frontend checks: `npm test`,
     `node scripts/walkthrough.mjs`, `npm run a11y` (see `specs/BACKEND_HANDOFF.md`).
   - The dev server proxies `/api` to `localhost:8000`, but **port 8000 is taken on this
     machine by another project**: run the API on 8001 and point the proxy there, or
     free 8000.
2. **Deploy (C12):** the user creates the Railway service and Postgres with pgvector;
   steps are in `backend/README.md` "Deploy (Railway)". `railway.json` runs `lens release`
   before each deploy.
3. **README (step 15):** top-level README with the real `lens eval` table.

## Decisions already made (don't reopen)

- **Gate:** every golden item passes and citation validity is 100% (SPEC C11). The mean
  is only the displayed score; `--gate` stays for future live evals.
- **Finding wording:** keep the technical `how`; `why` lines are plain English.
- **`Summary.clash` / `long_horizon`** are nullable (`types.ts` and models); the UI hides
  them when null. The RFI page has an empty-state message.
- **Retrieval `top_k` = 8** (at 6, hybrid recall was 7/8: a07 ranked 8th). a07 sits
  exactly at rank 8, on the edge.
- **`min_similarity` = 0.65**, from `lens ask calibrate`.
- **No `temperature`:** `claude-sonnet-5` rejects non-default sampling. **Thinking is off**
  for structured calls, so the forced tool call is guaranteed.
- **`GBP_PER_USD` = 0.75 is a placeholder** the user hasn't confirmed.
- **Ask is deliberately not agentic** (two model calls, verified output, replayable).
- Condition numbers come from paragraph headings (C6); cross-document citations are
  rejected (C5); `asset_properties` is a top-level list in `ExtractionResult` (C4).

## Environment quirks on this machine

- Postgres for this project runs from `docker-compose.yml` on **port 5433**
  (`LENS_DB_PORT=5433 docker compose up -d --wait db`); 5432 belongs to another
  project's container (`tasker-postgres-1`).
- **Port 8000** is used by another project's uvicorn. Use 8001 (API) and 8002 (the
  compose `app` profile) for checks.
- Run `uv run lens …` **inside `backend/`**; from the repo root `lens` isn't found.
- fastembed/onnxruntime can drop a `:memory:.ses` telemetry file in the working
  directory; `*.ses` is gitignored.

## How the tests stay honest without recordings

`backend/tests/perfect_extraction.py` is a hand-written correct extraction of the five
documents, and `tests/perfect_ask.py` answers Ask's calls from `evals/ask_golden.jsonl`.
`tests/test_consolidate.py::PerfectTransport` serves both through the real record/replay
adapter, so the verifier, consolidation, checks, API, eval and Ask are tested end to end.
The recorded-model tests compare the real model's answers with the same answer key.
