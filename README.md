# DataRoom Lens

DataRoom Lens reads the documents for a renewable energy deal and tells a lawyer three things: what is wrong, what is missing, and what to ask the seller. Every point it makes comes with the exact words from the document it relied on, so nothing has to be taken on trust.

**Try it:** https://app-production-1a86.up.railway.app

The deal in the demo is made up. It is a 49.9 MW solar farm with battery storage called Brackenfield Solar & Storage, at Wickham in the UK. The five documents were written for the demo and contain some deliberate problems for the tool to find.

---

## The problem it solves

When someone buys a solar farm, their lawyers read every document in the seller's "data room": the land lease, the planning permission, the grid connection offer, the contract to sell the electricity, and so on. The hard part is not reading each one. It is checking that they all fit together.

For example:

- The contract to sell the electricity expects the farm to be running by **31 March 2029**.
- The grid connection offer says the farm will not be connected until **1 October 2029**.

Each document is fine on its own. Together they mean the farm cannot run for about six months after it has promised to. Spotting that means holding two documents in your head at once, and a real deal has dozens. DataRoom Lens does that cross-checking, shows its working, and lets a lawyer confirm or correct each point.

---

## A tour of the app

### Summary

The first screen gives the headline, for example:

> Five findings. One critical gap: nothing gives the project rights to reach the grid.

Below it are the key facts (export capacity, grid connection date, lease term, who buys the power), a timeline of the important dates, and the list of findings, most serious first. In the demo those are:

| # | Finding | What it means in plain words |
|---|---|---|
| 1 | No rights for the export cable across Parcels 14 and 15 | The cable to the grid crosses two plots of land, and nothing in the data room gives the project the right to use them. |
| 2 | Grid connection falls 184 days after the PPA target COD | The grid connection comes about six months after the date the electricity contract expects the farm to be running. |
| 3 | Export capacity is 49.9 MW in two documents and 45 MW in the grid offer | The documents disagree about how much power the farm can send to the grid. |
| 4 | Lease ends about nine years before the permitted operating life | Planning allows the farm to run until about 2069, but the land lease ends in 2060. |
| 5 | Pre-commencement Condition 5 has no discharge on file | The council said no work may start until it approves a traffic plan, and there is no record of that approval. |

Three more checks passed, and you can see those too.

### Evidence

Open any finding to see why it was raised. The left side explains it in plain English. The right side shows the actual page from the document with the relevant words highlighted. A reviewer can then:

- **Accept** the finding,
- **Reject** it with a reason, or
- **Correct** it, for example "these two capacity figures are different things, so this is not a conflict".

Every correction is remembered and becomes a test the system has to keep passing (see "The accuracy check" below).

### Documents

A list of everything in the data room, and everything that should be there but isn't. The demo is missing two documents: the easement for the cable route, and the council's approval of the traffic plan.

Open a document to read it page by page. Every passage the tool relied on is highlighted, and the margin shows what it took from that passage. For example, next to a planning condition you will see:

> Condition 5: No work may start until the Construction Traffic Management Plan is approved

and a link to the finding it led to.

### Seller questions

The formal questions to send to the seller, one for each gap. For example:

> Please provide the executed deed(s) of easement for the export cable across Parcels 14 and 15 to Wickham Primary Substation.

They download as a document ready to send. They contain nothing internal to the tool.

### Ask

Ask a question in plain English, such as "What is the target commercial operation date?". The answer comes back in a sentence or two, and every sentence links to the passage it came from.

If the documents do not say, it says so instead of guessing. For example, "How large is the decommissioning bond?" gets the answer that the data room does not cover it, with a suggestion to ask the seller.

---

## Why you can trust what it says

**Every fact is a quote.** The AI is asked to find facts and copy the exact words that support them. Ordinary code then checks that those words really appear in the document, character for character, and that the number or date in the fact is actually in those words. If the check fails, the fact is thrown away.

**It does not pick a side.** When documents disagree, such as the 49.9 MW and 45 MW figures above, it reports the disagreement and shows both sources. It never quietly chooses one.

**Missing is not the same as wrong.** If a document that should exist is not there, the finding says "document missing" and becomes a question for the seller. It does not assume the worst.

**The AI does only three narrow jobs.** It reads each document once to pull out facts, it decides what kind of question you asked, and it drafts short answers to simple questions. Everything else, including every finding, every sentence of explanation, and every seller question, is written by fixed rules in code, so the same documents always give the same result.

**It is checked against an answer key.** See the next section.

---

## The accuracy check

The project keeps an answer key: the facts, conflicts and results that a careful lawyer would expect from these documents, plus a set of questions with known answers. Every change is tested against it, and the site will not go live if any example fails.

When a reviewer corrects a finding in the app, that correction is added to the answer key as a new example, so the system is held to it from then on.

Here is the latest result:

| What is checked | Result | In plain words |
|---|---|---|
| Facts and links between documents | 15 of 15 | Every fact in the answer key was found, quoted from the right place. |
| Conflicts | 1 of 1 | The capacity disagreement was spotted. |
| Check results | 3 of 3 | The checks in the answer key came out as expected. |
| Reviewer corrections | 1 of 1 still hold | A correction made by a reviewer is still respected. |
| Quote accuracy | 100% | Every quote shown matches the document exactly. |
| Finding the right passages for Ask | 8 of 8 | For every question with an answer, the right paragraph was found. |
| Ask answers | 12 of 12 | Every answerable question got the right answer. |
| Knowing when not to answer | 3 of 3 | Every question the documents cannot answer was declined. |
| **Overall** | **1.000, passing** | The bar to go live is 0.90, and every single example must pass. |

Running all of this against the real AI would cost about 16p. In practice it costs nothing, because the AI's answers are recorded once and replayed (see below).

---

## How it works

Think of it as an assembly line with six stations.

1. **Read.** The PDFs are split into pages and paragraphs. Each paragraph gets a label, such as "planning decision, page 3, paragraph 6", so it can be quoted exactly later.
2. **Extract.** The AI reads one document at a time and lists the facts it finds, each with the exact words that support it. For example: export capacity 49.9 MW, supported by "maximum export capacity of 49.9MW".
3. **Verify.** Code checks every fact against its quote. A quote that isn't word for word in the document, or that doesn't contain the value, is rejected.
4. **Combine.** Facts from all five documents are joined into one picture of the deal. "Brackenfield Solar Ltd" in one document and "Brackenfield Solar Limited" in another are recognised as the same company.
5. **Check.** Eight checks run over that picture. For example: does the grid connection come before the date the electricity contract expects the farm to run? Does the lease last as long as the planning permission allows?
6. **Report.** Each check produces a finding with its evidence, and each gap produces a seller question, all worded by fixed templates.

**Recorded answers.** The AI's responses are saved to files the first time they are generated. After that, the whole pipeline replays those files, which means it gives the same answer every time, runs without an API key, and costs nothing. The live site replays them too. Only Ask questions that were not recorded in advance go to the AI live, and those are capped at 20 per visitor per day and £5 a day in total.

---

## Run it on your computer

### The quickest way: just the screens

This runs the app on built-in sample data. You only need Node.js (version 22).

```bash
cd frontend
npm ci
npm run dev
```

Then open http://localhost:5173. Everything works, including reviews and seller questions. Nothing is saved when you close it.

### The full version: screens and the real backend

You also need [Docker](https://www.docker.com/) (to run the database) and [uv](https://docs.astral.sh/uv/) (to run the Python backend).

**1. Start the database** (from the top folder of the project):

```bash
docker compose up -d --wait db
```

If you already have something using port 5432, pick another port:

```bash
LENS_DB_PORT=5433 docker compose up -d --wait db
```

and tell the backend where to find it:

```bash
export DATABASE_URL=postgresql://lens:lens@localhost:5433/lens
```

**2. Prepare the backend** (in the `backend` folder). Each step builds on the one before:

```bash
cd backend
uv sync                      # install
uv run lens migrate          # create the database tables
uv run lens ingest           # read the PDFs into paragraphs
uv run lens run --publish    # run the assembly line, replaying the recorded answers
uv run lens index            # prepare the documents for Ask
uv run lens seed             # add the demo's example reviews
uv run lens eval             # run the accuracy check; it should say PASSING
```

**3. Start the backend:**

```bash
uv run uvicorn app.main:app
```

Check it is working by opening http://localhost:8000/api/health.

**4. Start the screens against it** (in a second terminal):

```bash
cd frontend
VITE_USE_FIXTURES=false npm run dev
```

If the backend is not on port 8000, add its address, for example `LENS_API_URL=http://localhost:8001`.

No API key is needed for any of this. You only need one to record fresh AI answers (`uv run lens record`) or to let Ask answer questions it has not seen before.

---

## What's in the project

| Folder | What it holds |
|---|---|
| `frontend/` | The screens: React and TypeScript. |
| `backend/` | The server and the assembly line: Python with FastAPI and PostgreSQL. |
| `backend/checks/` | The eight checks, one file each, including the wording of each finding. |
| `backend/fixtures/llm/` | The recorded AI answers that the pipeline replays. |
| `data/dataroom/` | The demo's five documents, as PDFs and the text they were made from. |
| `design/` | The shared definition of what the backend sends and the screens expect, the sample data, and the colours and fonts. |
| `evals/` | The answer key used by the accuracy check. |
| `specs/SPEC.md` | The detailed technical specification for the backend. |

---

## For developers

The rules for working on the code are in `CLAUDE.md`. The main ones: never show a fact without a checked quote, keep all wording in code rather than asking the AI to write it, and never edit the answer key or the sample data just to make a test pass.

Checks that run on every change:

```bash
# backend (in backend/)
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
uv run python tools/check_dataroom.py
uv run python tools/check_templates.py
uv run python tools/check_ask.py

# frontend (in frontend/)
npm test
npm run build
npm run a11y                     # accessibility, light and dark (needs the dev server)
node scripts/walkthrough.mjs     # the whole demo, by keyboard only (needs the dev server)
```

Deploying to Railway is described in `backend/README.md`.

---

## Limits worth knowing

- **One made-up deal.** The checks and wording are written for this kind of asset and these kinds of documents. A different deal would need its own checks.
- **It supports a lawyer, it does not replace one.** It finds, quotes and organises. The judgement stays with the reviewer, which is why every finding can be accepted, rejected or corrected.
- **Live questions have a budget.** Ask's free-form questions stop for the day at the limits above. The suggested questions always work.
