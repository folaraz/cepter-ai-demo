# Backend

FastAPI service for DataRoom Lens. Spec: `../specs/SPEC.md`. It implements the endpoints listed at
the bottom of `../design/api/types.ts` and `../design/api/ask.types.ts` and returns exactly
those shapes. The frontend switches over by setting `VITE_USE_FIXTURES=false`; in dev it
proxies `/api` to `http://localhost:8000`.

## Run locally

```bash
cd backend
uv sync
docker compose -f ../docker-compose.yml up -d --wait db
uv run lens migrate
uv run lens ingest      # PDFs -> documents and paragraphs; skips unchanged files
uv run lens run --publish   # the pipeline, replaying recorded model responses
uv run lens index           # embed every paragraph for Ask (skips unchanged)
uv run lens seed            # the demo's seed reviews
uv run uvicorn app.main:app
curl localhost:8000/api/health
```

If port 5432 is taken, start the database with `LENS_DB_PORT=5433` and set
`DATABASE_URL=postgresql://lens:lens@localhost:5433/lens`.

## Settings

| Variable | Default |
|---|---|
| `DATABASE_URL` | `postgresql://lens:lens@localhost:5432/lens` |
| `LLM_MODE` | `replay` (`record`, `live`) |
| `LLM_MODEL` | `claude-sonnet-5-5` |
| `ANTHROPIC_API_KEY` | unset; only needed to record, or for live Ask |
| `ASK_LIVE` | `false` |
| `EMBEDDING_CACHE_DIR` | `./.models` |
| `COOKIE_SECURE` | `false` |
| `EVAL_GATE` | `0.90` |
| `FRONTEND_DIST` | `../frontend/dist`: the built UI, served at `/` when present |
| `GBP_PER_USD` | `0.75`: placeholder; model prices are in USD, `llm_calls.cost_gbp` is GBP |

## Checks

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
uv run python tools/check_dataroom.py
uv run python tools/check_templates.py
uv run python tools/check_ask.py
```

## Ask

`POST /api/ask` answers a question about the data room, or says it can't. The model
routes the question and drafts lookup answers; code checks the route against
`ask.yaml`, renders relationship answers from its templates, and verifies every lookup
sentence (verbatim quotes from retrieved paragraphs, no number or date its quotes don't
state). Model calls replay recordings; without one, a call goes live only with
`ASK_LIVE=true` and within the limits in `ask.yaml`, otherwise the answer is
"unavailable". `GET /api/ask/suggestions` lists the recorded suggested questions.

## Retrieval (Ask)

`lens index` stores one embedded chunk per paragraph (bge-small, 384 dimensions, local).
Search fuses vector and keyword search by reciprocal rank. `uv run lens ask calibrate`
prints, for every golden Ask question, the best similarity and where each expected
paragraph ranks under vector, keyword and hybrid search.

## Accuracy check (eval)

`uv run lens eval [--session S] [--gate 0.90] [--json]` re-runs the pipeline on the
recorded model responses and scores it against `evals/golden.jsonl` (plus a session's
corrections). It prints a table and exits 1 when failing. On the hand-written perfect
extraction the tests use:

```
Metric                                      Result
--------------------------------------------------
Extraction (facts and edges)                 15/15
Conflicts                                      1/1
Checks                                         3/3
Corrections held                   1/1 (1 learned)
Citation validity                             100%
```

Passing needs **every** golden item to pass and 100% citation validity: an average can
hide a broken check, so each item is its own gate. The score (the mean) is what the UI
shows. A correction holds only while the paragraphs it cited are unchanged. CI runs the gate once
recordings are committed. `POST /api/evals/run` runs it for a visitor's session.

## The UI

With a build in `frontend/dist` (`npm run build` in `frontend/`), the API also serves
the app at `/`: files in `dist` as themselves, any other non-`/api` path as
`index.html`. `tests/test_api_types.py` fails if a response model drifts from
`design/api/types.ts`.

## Model calls

`app/llm/` is the only code that talks to Claude. Each call runs in a mode: `replay`
(default; reads `fixtures/llm/{key}.json` and raises `MissingRecording` if it is absent),
`record` (calls the API and writes the file), `live` (calls without writing) or
`replay_first` (Ask only). Every call writes an `llm_calls` row. No temperature is sent:
`claude-sonnet-5-5` rejects non-default sampling parameters, and replay is what makes runs
repeatable.

To record model responses (needs an API key; nothing else does). Record both before
committing: the release step and CI's eval gate replay extraction *and* Ask.

```bash
export ANTHROPIC_API_KEY=...
uv run lens record              # one extraction call per document -> fixtures/llm/
uv run lens run --publish && uv run lens index
uv run lens record --ask        # routing and answers for evals/ask_golden.jsonl
git add fixtures/llm && git commit -m "Record extract.v1, ask.route.v1 and ask.answer.v1"
unset ANTHROPIC_API_KEY
```

Changing the extraction prompt changes the recording keys: bump `PROMPT_VERSION` in
`app/extract/prompt.py` and record again.

## Reviews

Each visitor gets a private session (a `lens_session` cookie, 7 days). Their reviews
apply only to what they see; seed reviews (`lens seed`) apply to everyone. A reject or
correct becomes a golden item (`corr-002` onwards). To keep one as a CI test:

```bash
uv run lens golden export --session <session id>   # appends to evals/golden.jsonl
```

Session reviews, questions and eval runs older than 7 days are removed at startup.

## Deploy (Railway)

One service, built from the repo-root `Dockerfile`: Node builds the UI, then a Python
3.12 image with the embedding model downloaded at build time (the container never
fetches anything at runtime). Railway no longer reads `railway.json`, so the service's
settings are set on the service itself (dashboard or API).

1. **Postgres with pgvector.** Add a service from the official `pgvector/pgvector:pg16`
   image (Railway's `pgvector` template code resolves to a community repo; don't use it).
   Variables `POSTGRES_USER=lens`, `POSTGRES_DB=lens`, a random `POSTGRES_PASSWORD`, and
   `PGDATA=/var/lib/postgresql/data/pgdata`; a volume at `/var/lib/postgresql/data`.
2. **The app service.**

   | Setting | Value |
   |---|---|
   | `DATABASE_URL` | `postgresql://${{postgres.POSTGRES_USER}}:${{postgres.POSTGRES_PASSWORD}}@${{postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{postgres.POSTGRES_DB}}` |
   | `COOKIE_SECURE` | `true` (the site is served over HTTPS) |
   | `LLM_MODE` | `replay` (the image's default) |
   | `ASK_LIVE` | `false` unless live Ask is wanted (below) |
   | `RAILWAY_DOCKERFILE_PATH` | `Dockerfile` (without it Railway may build with Railpack and fail) |
   | Pre-deploy command | `lens release` |
   | Health check | `/api/health`, 120 s timeout |
   | Restart policy | on failure |

3. **Deploy** from a clean, up-to-date `main` checkout: `railway up --ci --service app`
   (until the repo is connected to Railway for deploy-on-push). Before it goes live,
   Railway runs `lens release`: migrate, ingest, run and publish the pipeline on the
   committed recordings, seed the demo's reviews, then the accuracy check. It stops at
   the first failure, and a failed release never goes live. It needs the
   `fixtures/llm/` recordings committed (`lens record`, above).
4. **Check** that the public URL opens on the Summary and `/api/health` reports the
   published run.

**Live Ask**: set `ASK_LIVE=true` and `ANTHROPIC_API_KEY`. Free-form
questions are then capped by `backend/ask.yaml` `limits`: 20 per session per day and a
£5.00 daily budget. Suggested questions always replay and never need the key.

**Locally, the same image:** `docker compose --profile app up --build` (set
`LENS_APP_PORT` if 8000 is taken). Logs are JSON lines, each with `request_id` and,
inside a pipeline run, `run_id`; responses echo `X-Request-ID`.

PyMuPDF is AGPL, which is fine for a demo; a commercial build would swap it for
pypdfium2 or pdfplumber.
