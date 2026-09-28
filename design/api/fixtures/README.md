# API fixtures: the one copy of the contract's data

These files are three things at once, so there is only one copy of each:

- the UI's fixture mode reads them (`frontend/src/api/client.ts`, via `@design/api/fixtures`);
- the backend's contract test compares every endpoint's JSON with them
  (`backend/tests/test_contract.py`, under the rules below);
- `backend/tools/check_dataroom.py`, `check_templates.py` and `check_ask.py` prove the
  data room and the wording files can produce them.

So fixture mode and the real API show the same data. Change a file here only when the
product's output changes on purpose, and never to make a test pass.

## Three deliberate updates to the original UI fixtures

| Field | Fixture | Expected | Why |
|---|---|---|---|
| `summary.documents[].pages` | 14, 6, 22, 31, 3 | 3, 3, 3, 5, 2 | The real page counts of the committed synthetic PDFs. |
| `summary.missing_documents` | 1 item | 2 items | The Condition 5 discharge is also expected and missing; the backend lists every missing-evidence finding that names a document. |
| `summary.facts[network_operator].value` | "Fenland Distribution" | "Fenland Distribution Networks" | The display rule only strips the legal suffix ("plc"); it does not shorten names. |

Ask is not compared here: its expectations are `evals/ask_golden.jsonl` (C14), and its UI
fixtures in `design/api/fixtures/ask/` are verified by `backend/tools/check_ask.py`.

## Documents

`documents.json` and `documents/{id}.json` are `GET /api/documents` and
`GET /api/documents/{id}` over the hand-written correct extraction. Each note's wording
comes from `backend/documents_view.yaml`; the contract test compares them exactly.

## Fields the contract test does not compare exactly

| Field | Rule instead |
|---|---|
| `summary.run.id`, `summary.run.at`, `eval.last_run_at` | Present and correctly typed. |
| `eval.score`, `eval.cost_gbp`, `eval.golden_count`, `eval.corrections_*` | Present, in range; exact values come from `lens eval`. |
| `evidence[].citation.quote`, `quote_start`, `quote_end` | The quote may differ from the fixture (the model chooses the span), but it must be a verbatim substring of `paragraph_text`, contain the value, and match its offsets. |

Everything else (IDs, titles, why/how text, severities, results, paragraph IDs,
paragraph text, headings, roles, RFI wording, dates, facts) must match exactly.
`backend/tools/check_dataroom.py` and `backend/tools/check_templates.py` already prove
the data room and the check templates can produce these values.
