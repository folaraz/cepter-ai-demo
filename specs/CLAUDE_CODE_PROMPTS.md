# Claude Code prompts for the backend

Run these in order from the repo root, one prompt per task. After each: run the
"check" line, commit, move on. Times assume things go smoothly. The cut order is in
`specs/SPEC.md` section 5.

You need an Anthropic API key twice, on your laptop only: step 4 (recording extraction)
and step 12 (recording the Ask golden questions). Nothing else calls the API unless you
turn on free-form Ask in production.

## 0. Add the backend rules to CLAUDE.md (2 min, do it yourself)

```
## Backend rules
- The backend spec is specs/SPEC.md. The API contract is design/api/types.ts and
  design/api/ask.types.ts. Expected output is backend/tests/contract/expected/ (read its
  README) and, for Ask, evals/ask_golden.jsonl.
- Never store or serve a fact or an answer sentence without a verified quote. Absence
  statements link to the finding that established them instead. Rejected claims stay in
  `claims`; dropped answer sentences are counted, never shown.
- The model does three things only: extraction (pass 1), routing an Ask question, and
  drafting a lookup answer. Verification, merging, checks, all finding/summary/RFI
  wording, relationship answers and evals are deterministic Python.
- Tests and CI run with no API key: LLM_MODE=replay, and Ask uses recordings. A missing
  recording must raise, never fall back to the API.
- Do not edit data/dataroom/pdf/, evals/golden.jsonl, evals/ask_golden.jsonl or
  tests/contract/expected/ to make a test pass. If they look wrong, stop and say so.
- Plain SQL via psycopg 3; no ORM. Pydantic 2 models at every boundary.
- Keep backend/tools/check_dataroom.py, check_templates.py and check_ask.py green.
```

## 1. Skeleton, CI and database (C0, C2) · 1 h

```
Read specs/SPEC.md sections 1–4 (C0 and C2). Create the backend app in backend/app
with the layout in section 3: FastAPI app with GET /api/health, pydantic-settings config
with the variables listed in C0, a psycopg 3 connection pool with the pgvector adapter
registered, `lens migrate` (typer CLI in app/cli.py, installed as the `lens` script via
pyproject.toml) that applies backend/schema.sql, and thin repositories in app/db/repositories/
for every table. Add docker-compose.yml with the pgvector/pgvector:pg16 image, ruff,
mypy (strict for app/domain and app/verify), pytest, pre-commit, and a GitHub Actions
workflow with a pgvector/pgvector:pg16 service container that caches
EMBEDDING_CACHE_DIR and runs lint, types, tests, python backend/tools/check_dataroom.py,
check_templates.py and check_ask.py. Add a repository round-trip test per table.
Don't build any pipeline code yet.
```

Check: `docker compose up -d db && lens migrate && pytest && curl localhost:8000/api/health`

## 2. Ingestion (C1) · 45 min

```
Implement C1 from specs/SPEC.md. Port backend/tools/check_dataroom.py's ingest()
into app/ingest/pdf.py without changing its rules (header/footer margin, bold-heading
detection, hyphen line joins, NFKC, per-page paragraph numbering). Add `lens ingest`,
which reads data/dataroom/manifest.yaml and upserts documents (sha256, page count) and
paragraphs, skipping unchanged files. Write tests/test_ingest.py: the production
ingester must equal the reference paragraph-for-paragraph (55 paragraphs), two runs
must be identical, ppa:p4:¶2 must contain "Long-Stop Date", and no paragraph may
contain the running header or footer.
```

Check: `lens ingest && pytest tests/test_ingest.py`

## 3. LLM adapter with record/replay (C3) · 1 h

```
Implement C3 from specs/SPEC.md: the LLMClient protocol with a per-call mode, the
Anthropic client using one forced tool whose input_schema is the Pydantic schema
(temperature 0, one retry on validation error), the recording key and file format
(including caller metadata), the replay/record/live/replay_first modes with
MissingRecording on a replay miss, llm_calls rows for every call, and
app/llm/pricing.py with a per-model price table (leave the numbers as TODOs with a
comment to fill them from the current price list; do not invent prices). Tests must not
touch the network: use a fake transport for record and live modes.
```

Check: `pytest tests/test_llm.py`

## 4. Extraction and recording (C4) · 1.5 h

```
Implement C4 from specs/SPEC.md: Pydantic models in app/domain/ontology.py and
app/domain/extraction.py written from backend/ontology.yaml (add a test that the enums
and property names match the YAML), the extract.v1 prompt with every rule in C4, and
app/extract/pass1.py that runs one call per document and stores results as claims
pending verification. Add `lens record` (extraction only for now) and `lens run` (full
pipeline, replay by default). Stop after writing the code: I will run `lens record`
myself.
```

Then, yourself:

```bash
export ANTHROPIC_API_KEY=...        # only here and in step 12, never in CI
LLM_MODE=record lens record
git add backend/fixtures/llm && git commit -m "Record extract.v1 responses"
unset ANTHROPIC_API_KEY
```

Check: `lens run` works with no key set.

## 5. Verifier (C5) · 1 h. Never cut.

```
Implement C5 from specs/SPEC.md in app/verify/. Pure Python, no LLM. Implement every
verify kind from backend/ontology.yaml, the one-for-one quote normalisation, offsets on
the display text, and storing the canonical quote as paragraph.text[start:end]. Expose
the quote check and the number and date extractors as public functions (Ask reuses
them). Write the unit tests listed under "Done when", plus a test that runs the verifier
over the replayed claims and prints how many were rejected and why.
```

Check: `pytest tests/test_verifier.py -v`

## 6. Consolidation (C6) · 1.5 h

```
Implement C6 from specs/SPEC.md in app/consolidate/: node resolution by the merge
rules in backend/ontology.yaml, name normalisation for companies and people, property
groups with the corroborated/verified/conflict rules, many:true properties, party
identity status, and nodes/edges/provenance rows. Write tests/test_consolidate.py that
runs the replayed pipeline and asserts everything in data/dataroom/planted_facts.yaml
under facts, edges, absent and consolidation.
```

Check: `lens run && pytest tests/test_consolidate.py -v`. If a planted fact is missing,
fix the prompt (bump to `extract.v2`) and re-record; don't loosen the test.

## 7. Retrieval index (C13) · 1.5 h

```
Implement C13 from specs/SPEC.md: app/retrieval/embed.py (fastembed model from
backend/ask.yaml, loaded once, cached in EMBEDDING_CACHE_DIR, unit-length vectors),
`lens index` (one chunk per paragraph, content from ask.yaml chunk_text, idempotent,
never writing the generated tsv column), app/retrieval/search.py with vector search,
the OR keyword query from ask.yaml, and reciprocal rank fusion returning ranks,
similarity and fused score, and `lens ask calibrate` printing, per golden question in
evals/ask_golden.jsonl, the best similarity and each expected paragraph's rank under
vector, keyword and hybrid search. Test hybrid recall@6 for all eight golden lookups and
that keyword-only search misses a07.
```

Check: `lens index && lens ask calibrate && pytest tests/test_retrieval.py -v`. Set
`min_similarity` in `backend/ask.yaml` from the calibrate output.

## 8. Check runner (C7) · 2 h. Never cut.

```
Implement C7 from specs/SPEC.md. The runner loads backend/checks/*.yaml, applies the
refuse-to-guess rule, calls one registered implementation per check (app/checks/impl/),
assigns RFI IDs (C8 ordering) before rendering, renders with str.format, builds
evidence in input order with one card per paragraph, and stores one findings row per
check with ID F-{order:02d}, keeping each outcome's context and input provenance for
Ask. Put wording helpers (short dates, parcel prose, ranges with an en dash, number
words, noun lists) in app/checks/render.py with unit tests. Test that results, finding
IDs, evidence order and every context value equal data/dataroom/planted_facts.yaml, and
that rendered title/why/how/missing strings equal
backend/tests/contract/expected/findings/*.json.
```

Check: `lens run && pytest tests/test_checks.py -v`

## 9. Summary, RFIs and read endpoints (C8, C10) · 1.5 h

```
Implement C8 and the read side of C10 from specs/SPEC.md: the summary builder
following backend/summary_view.yaml, the RFI builder and Markdown export, Pydantic
response models in app/api/models.py mirroring design/api/types.ts, and GET
/api/summary, /api/findings/{id}, /api/rfi and /api/rfi.md reading the published run.
Write tests/test_contract.py as described in C10 (fresh database, replayed pipeline,
seeded reviews, compare with backend/tests/contract/expected/ using the rules in its
README). Skip the eval fields for now.
```

Check: `pytest tests/test_contract.py -v`

## 10. Reviews, sessions and undo (C9) · 1 h. Never cut.

```
Implement C9 from specs/SPEC.md: the session cookie middleware, visible reviews
(seed plus session), POST /api/findings/{id}/review with accept, reject and correct,
evidence fingerprints, corr-NNN numbering, POST /api/reviews/undo, `lens seed` for
backend/seed/reviews.yaml, `lens golden export --session`, and startup housekeeping
(reviews, asks and eval runs older than 7 days). Test the demo sequence from
"Done when" through the API with two separate sessions. Mark the eval state as stale
using a placeholder until step 11 replaces it.
```

Check: `pytest tests/test_reviews.py -v`

## 11. Eval harness, gate and eval endpoints (C11) · 1.5 h. Never cut.

```
Implement C11 from specs/SPEC.md except the three Ask metrics (step 12 adds them):
the derived golden set (base file plus session corrections, corrections superseding
check items, golden_hash), `lens eval` with the metrics, effective results with the
fingerprint rule, the learned metric, the gate, the printed table and non-zero exit on
failure, a --no-ask flag, POST /api/evals/run as a background task with one run per
session, and GET /api/evals/latest with the stale rule. Put the eval status into the
summary and the review response. Add `lens eval --gate 0.90` as the last CI step.
Tests: a deliberately broken check fails the gate; an edited cited paragraph makes a
correction lapse; the full demo sequence ends passing with 2 of 2 corrections held.
```

Check: `lens eval --no-ask --gate 0.90` prints extraction 15/15, conflicts 1/1, checks
3/3, corrections 1/1 held (1 learned), citation validity 100%.

## 12. Ask (C14) · 2 h. Never cut: answer verification and abstention.

```
Implement C14 from specs/SPEC.md: Pydantic models in app/domain/ask.py mirroring
design/api/ask.types.ts; app/ask/router.py (ask.route.v1, replay_first, validated
against backend/ask.yaml with fallback to lookup); app/ask/graph_queries.py running the
four graph queries in ask.yaml over the published run and rendering their templates,
with citations from provenance and finding_id on absence sentences; app/ask/answer.py
(retrieval from step 7, the early-exit rule, ask.answer.v1 with paragraphs in document
order, and step 6's sentence verification using the verifier's public functions);
app/ask/service.py with validation, cache, related finding/RFI, ASK_LIVE and the limits,
and the asks table; POST /api/ask and GET /api/ask/suggestions; `lens record --ask`
storing the retrieved paragraph IDs in recording metadata, and RetrievalDrift in replay.
Then add the three Ask metrics and Ask citations to `lens eval` (C11). Write
tests/test_ask.py and the unit tests from "Done when". Stop before recording: I will run
`lens record --ask` myself.
```

Then, yourself:

```bash
export ANTHROPIC_API_KEY=...
LLM_MODE=record lens record --ask
git add backend/fixtures/llm && git commit -m "Record ask.route.v1 and ask.answer.v1 for the golden questions"
unset ANTHROPIC_API_KEY
```

Check: `pytest tests/test_ask.py -v && lens eval --gate 0.90` shows retrieval recall 8/8,
answer accuracy 12/12 and abstention 3/3. If an answer fails, fix the prompt (bump the
version) and re-record; don't edit the golden set.

## 13. Switch the UI to the real API (C10) · 30 min

```
Serve frontend/dist from FastAPI at / with an SPA fallback. Copy
backend/tests/contract/expected/summary.json over frontend/src/api/fixtures/summary.json.
Set VITE_USE_FIXTURES=false, generate frontend/src/api/schema.ts from the FastAPI
OpenAPI schema with openapi-typescript, make client.ts use it, and report any field
that differs from design/api/types.ts or design/api/ask.types.ts. Fix the backend or the
client until fixture mode and the live API render identically. askQuestion and
getAskSuggestions already exist from design/CLAUDE_CODE_PROMPTS.md step 9; point them at
POST /api/ask and GET /api/ask/suggestions and confirm the five suggested questions render
the same as their fixtures.
```

Check: run both modes side by side and walk the demo: open F-03, step through sources,
correct it, run the eval, undo, export RFIs. Call `/api/ask` with each suggested question.

## 14. Deploy (C12) · 1.5 h. Never cut.

```
Implement C12 from specs/SPEC.md: a multi-stage Dockerfile (Node builds
frontend/dist; Python 3.12 runtime that downloads the embedding model into
EMBEDDING_CACHE_DIR at build time), the release command
`lens migrate && lens ingest && lens run --publish && lens index && lens seed && lens eval`,
LLM_MODE=replay, ASK_LIVE=false by default, JSON logging with run_id and request id,
and README instructions for creating the Railway service and a Postgres with pgvector,
plus how to turn on live Ask with a key and the caps. Verify the container locally with
docker compose before deploying.
```

Check: the public URL opens on the Summary, the demo sequence works, and every suggested
question answers with no API key set.

## 15. README (30 min, optional prompt)

```
Write README.md for reviewers at Cepter: one paragraph on what this is, the live link,
a 60-second walkthrough of the demo sequence and two Ask questions (one answered with
citations, one abstained), the architecture as three passes plus checks plus Ask (the
model proposes; code verifies and decides), the output of `lens eval` as a table
including keyword-only vs hybrid recall, how a reviewer correction becomes a regression
test and why overrides lapse when cited text changes, why answers are verified rather
than streamed, how to run it locally with no API key, and "What I'd do next": split
export capacity into permitted/contracted/grid properties (the correction story), grow
the Ask golden set from real questions, OCR, a commercial PDF library instead of
PyMuPDF, Temporal for long-running ingestion. Label the data room as synthetic.
```
