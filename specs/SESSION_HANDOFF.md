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

## Immediate next step: finish the recordings

The user is recording the real model's answers (needs `ANTHROPIC_API_KEY`, laptop
only). **Nothing in `backend/fixtures/llm/` is committed yet.** As of this handoff the
folder holds 26 uncommitted recordings: 5 × `extract.v2`, 15 × `ask.route.v1`,
6 × `ask.answer.v1`.

What the `extract.v2` recordings show (`pytest -s tests/test_verifier.py::test_verifier_over_the_recorded_extraction`):
74 claims, **1 rejected**:

- grid offer `PARTY_TO` customer, quoting `grid_offer:p2:¶2` ("The Customer shall
  construct the export cable…"), which doesn't name the company, so the verifier's name
  rule rejects it. The right paragraph is `grid_offer:p1:¶2` ("…made by Fenland
  Distribution Networks plc to Brackenfield Solar Limited."). Effect: F-07
  (`parties_consistent`) is `missing_evidence`, not `pass`, and the answer-key test for
  that edge fails.

**Fix (next session):** bump to `extract.v3` in `backend/app/extract/prompt.py` with a
rule like "cite the paragraph where the party is named in that role (for example the
opening parties clause), not a later clause that uses the role on its own". Then the user
re-records extraction. Don't loosen tests or the verifier. The build prompts say to fix
the prompt and re-record.

Also confirm `lens record --ask` completed. Six answer recordings may be short: eight
lookups plus x01 reach the answer model, unless the early exit fires; x02 is expected to
exit early. `lens eval` will say.

Then the user runs, from `backend/`:

```bash
rm fixtures/llm/*.json   # only if re-recording everything; keys change with prompt versions
export DATABASE_URL=postgresql://lens:lens@localhost:5433/lens ANTHROPIC_API_KEY=...
uv run lens record
uv run lens run --publish && uv run lens index
uv run lens record --ask
uv run lens eval          # must print PASSING; every golden item is its own gate
git add fixtures/llm && git commit -m "Record extract.v3, ask.route.v1 and ask.answer.v1"
unset ANTHROPIC_API_KEY
```

The recorded-model tests (`test_*_over_the_recorded_extraction`, the contract test's
recorded variant) stop skipping once recordings match. They're the check that the real
model meets the answer key.

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
