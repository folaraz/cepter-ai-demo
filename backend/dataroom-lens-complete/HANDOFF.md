# DataRoom Lens: complete handoff

Everything needed to finish DataRoom Lens: the UI design, the backend spec, the synthetic
data room, both answer keys, and the Claude Code prompts, in one coherent set. Unzip at
the repo root. It adds `design/`, `backend/`, `data/` and `evals/` and replaces older
copies of the same files, so if you edited any of them, compare before overwriting.

**Live design (press Play):** https://claude.ai/artifact/QTUuik1ByprR9MvFnF5gvc

## What DataRoom Lens does

A diligence associate for one renewable-energy asset (Brackenfield Solar & Storage, a
synthetic data room of five documents). It shows what is wrong, what is missing and what to
ask the seller. Every fact, finding and answer cites a verbatim quote that code has verified.
A reviewer can accept, reject or correct any finding; each correction becomes a regression
test that the eval gate re-checks. Reviewers can ask questions; when the documents don't
answer, Ask says so instead of guessing.

## Map

| Folder | What | Start with |
|---|---|---|
| `design/` | UI spec, tokens, API contract (`api/types.ts`, `api/ask.types.ts`), fixtures, artboards | `design/DESIGN_HANDOFF.md` |
| `backend/` | Backend spec, schema, ontology, checks, Ask config, seed data, contract expectations, tools | `backend/SPEC.md` |
| `data/dataroom/` | The five synthetic documents (sources and committed PDFs), manifest, answer key | `planted_facts.yaml` |
| `evals/` | Golden set for findings (`golden.jsonl`, 20 items) and for Ask (`ask_golden.jsonl`, 15 questions) | |

One source of truth: `design/api/fixtures/` is identical to
`backend/tests/contract/expected/`, and the Ask fixtures are checked against the data
room, the golden set and `backend/ask.yaml`.

## Order of work

| Step | Where | Status |
|---|---|---|
| UI: Summary, Evidence, Requests, review loop | `design/CLAUDE_CODE_PROMPTS.md` steps 0–8 | Done |
| UI: Ask view, in fixture mode | `design/CLAUDE_CODE_PROMPTS.md` step 9 | Next |
| Backend, including Ask | `backend/CLAUDE_CODE_PROMPTS.md` steps 0–12 | Next |
| Switch the UI to the real API | `backend/CLAUDE_CODE_PROMPTS.md` step 13 | After the backend |
| Deploy and README | `backend/CLAUDE_CODE_PROMPTS.md` steps 14–15 | Last |

The Ask UI and the backend are independent until step 13, so they can run in parallel
Claude Code sessions. If you fall behind, the cut order is in `backend/SPEC.md` section 5.

## Checks (run from the repo root)

```bash
pip install -r backend/tools/requirements.txt
python backend/tools/check_dataroom.py    # PDFs reproduce every fixture citation exactly
python backend/tools/check_templates.py   # check templates reproduce the fixture wording (124 strings)
python backend/tools/check_ask.py         # Ask questions and Ask UI fixtures agree with the data room
```

All three pass on this bundle. CI runs them from backend step 1.

## API key

Needed on your laptop only: backend step 4 (recording extraction) and step 12 (recording
the Ask questions). CI, tests, the Summary and the five suggested Ask questions replay
recordings. Production needs a key only if you turn on free-form Ask (`ASK_LIVE=true`),
which is capped per session and per day.
