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
uv run lens run         # the pipeline, replaying recorded model responses
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
| `LLM_MODEL` | `claude-sonnet-5` |
| `ANTHROPIC_API_KEY` | unset; only needed to record, or for live Ask |
| `ASK_LIVE` | `false` |
| `EMBEDDING_CACHE_DIR` | `./.models` |
| `COOKIE_SECURE` | `false` |
| `EVAL_GATE` | `0.90` |
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

## Model calls

`app/llm/` is the only code that talks to Claude. Each call runs in a mode: `replay`
(default; reads `fixtures/llm/{key}.json` and raises `MissingRecording` if it is absent),
`record` (calls the API and writes the file), `live` (calls without writing) or
`replay_first` (Ask only). Every call writes an `llm_calls` row. No temperature is sent:
`claude-sonnet-5` rejects non-default sampling parameters, and replay is what makes runs
repeatable.

To record model responses (needs an API key; nothing else does):

```bash
export ANTHROPIC_API_KEY=...
uv run lens record              # one extraction call per document -> fixtures/llm/
git add fixtures/llm && git commit -m "Record extract.v1 responses"
unset ANTHROPIC_API_KEY
```

Changing the extraction prompt changes the recording keys: bump `PROMPT_VERSION` in
`app/extract/prompt.py` and record again.

PyMuPDF is AGPL, which is fine for a demo; a commercial build would swap it for
pypdfium2 or pdfplumber.
