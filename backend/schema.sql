-- DataRoom Lens schema. Applied on startup (idempotent). PostgreSQL 16.
-- No ORM: repositories in app/db/ run plain SQL and return Pydantic models.

-- pgvector for Ask retrieval. Local: the pgvector/pgvector:pg16 image. Railway: a
-- Postgres service with pgvector available; this statement fails loudly if it isn't.
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------- Source documents ----------

CREATE TABLE IF NOT EXISTS documents (
    id                text PRIMARY KEY,               -- manifest id: lease, planning, grid, ppa, site
    file_name         text NOT NULL,
    title             text NOT NULL,
    noun              text NOT NULL,
    paragraph_prefix  text NOT NULL UNIQUE,
    pages             int  NOT NULL CHECK (pages > 0),
    sha256            text NOT NULL,                  -- of the PDF bytes; changes force re-ingest
    ingested_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS paragraphs (
    id           text PRIMARY KEY,                    -- "grid_offer:p2:¶3"
    document_id  text NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page         int  NOT NULL,
    ordinal      int  NOT NULL,
    heading      text,
    text         text NOT NULL,                       -- display text (NFKC, whitespace collapsed)
    UNIQUE (document_id, page, ordinal)
);

-- ---------- Ask retrieval index (one chunk per paragraph) ----------

CREATE TABLE IF NOT EXISTS chunks (
    paragraph_id     text PRIMARY KEY REFERENCES paragraphs(id) ON DELETE CASCADE,
    document_id      text NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content          text NOT NULL,                   -- "{document title} — {heading}: {text}"
    embedding        vector(384) NOT NULL,
    embedding_model  text NOT NULL,                   -- a model change forces re-embedding
    tsv              tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED
);
CREATE INDEX IF NOT EXISTS chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv ON chunks USING gin (tsv);

-- ---------- Pipeline runs ----------

CREATE TABLE IF NOT EXISTS runs (
    id               text PRIMARY KEY,                -- "r-0921-a" style, or a uuid for eval runs
    kind             text NOT NULL CHECK (kind IN ('published', 'eval')),
    session_id       text,                            -- set for eval runs started from the UI
    as_of            date NOT NULL,
    status           text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'superseded')),
    prompt_versions  jsonb NOT NULL DEFAULT '{}',
    error            text,
    started_at       timestamptz NOT NULL DEFAULT now(),
    finished_at      timestamptz
);
-- Exactly one published run is live at a time. Publishing a new run marks the old one
-- 'superseded' and the new one 'succeeded' in the same transaction.
CREATE UNIQUE INDEX IF NOT EXISTS one_live_published_run
    ON runs ((kind)) WHERE kind = 'published' AND status = 'succeeded';

CREATE TABLE IF NOT EXISTS llm_calls (
    id              bigserial PRIMARY KEY,
    run_id          text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    purpose         text NOT NULL,                    -- "extract:lease", ...
    model           text NOT NULL,
    prompt_version  text NOT NULL,                    -- "extract.v1"
    request_hash    text NOT NULL,                    -- recording key
    input_tokens    int  NOT NULL,
    output_tokens   int  NOT NULL,
    latency_ms      int  NOT NULL,
    cost_gbp        numeric(10, 5) NOT NULL,          -- from the recording, so replay reports the live cost
    replayed        boolean NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------- Extraction (pass 1) and verification (pass 2) ----------

-- Every claim the model proposed, verified or not. Rejected claims never become facts.
CREATE TABLE IF NOT EXISTS claims (
    id                bigserial PRIMARY KEY,
    run_id            text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    document_id       text NOT NULL REFERENCES documents(id),
    kind              text NOT NULL CHECK (kind IN ('property', 'edge')),
    local_ref         jsonb NOT NULL,                 -- {"local_id": "gc1", "type": "GridConnection", "name": ...}
    property          text,                           -- for kind = property
    edge_type         text,                           -- for kind = edge
    target_ref        jsonb,                          -- for kind = edge
    value             jsonb,
    paragraph_id      text NOT NULL,                  -- as cited by the model; may not exist
    quote             text NOT NULL,
    status            text NOT NULL CHECK (status IN ('verified', 'rejected')),
    rejection_reason  text,                           -- 'no_such_paragraph' | 'quote_not_verbatim' | 'value_not_in_quote'
    quote_start       int,
    quote_end         int,
    CHECK ((status = 'verified') = (rejection_reason IS NULL))
);
CREATE INDEX IF NOT EXISTS claims_run ON claims (run_id, status);

-- ---------- Consolidated graph (pass 3) ----------

CREATE TABLE IF NOT EXISTS nodes (
    id          text PRIMARY KEY,                     -- "{run_id}:{type}:{key}"
    run_id      text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    type        text NOT NULL,
    key         text NOT NULL,                        -- merge key, e.g. normalised name or parcel number
    name        text,                                 -- canonical display name
    props       jsonb NOT NULL DEFAULT '{}',          -- consolidated values; conflicts keep every value
    UNIQUE (run_id, type, key)
);

CREATE TABLE IF NOT EXISTS edges (
    id         bigserial PRIMARY KEY,
    run_id     text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    type       text NOT NULL,
    source_id  text NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id  text NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    props      jsonb NOT NULL DEFAULT '{}',
    UNIQUE (run_id, type, source_id, target_id, props)
);

-- Links every fact in the graph to the verified claim that supports it.
CREATE TABLE IF NOT EXISTS provenance (
    id            bigserial PRIMARY KEY,
    run_id        text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    node_id       text REFERENCES nodes(id) ON DELETE CASCADE,
    edge_id       bigint REFERENCES edges(id) ON DELETE CASCADE,
    property      text,                               -- NULL for node identity or edge provenance
    value         jsonb,
    claim_id      bigint NOT NULL REFERENCES claims(id),
    document_id   text NOT NULL REFERENCES documents(id),
    paragraph_id  text NOT NULL REFERENCES paragraphs(id),
    quote         text NOT NULL,
    quote_start   int  NOT NULL,
    quote_end     int  NOT NULL,
    status        text NOT NULL CHECK (status IN ('verified', 'corroborated', 'conflict')),
    CHECK ((node_id IS NULL) <> (edge_id IS NULL))
);
CREATE INDEX IF NOT EXISTS provenance_node ON provenance (run_id, node_id, property);

-- ---------- Checks and findings ----------

-- One row per check per run, passes included (facts can link to a passed finding).
CREATE TABLE IF NOT EXISTS findings (
    run_id     text NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    id         text NOT NULL,                         -- "F-01", from check order, stable across runs
    check_id   text NOT NULL,
    severity   text NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    result     text NOT NULL CHECK (result IN ('fail', 'conflict', 'missing_evidence', 'pass')),
    title      text NOT NULL,
    why        text NOT NULL,
    how        text NOT NULL,
    context    jsonb NOT NULL,                        -- the template context, kept for debugging
    evidence   jsonb NOT NULL,                        -- Evidence[] as served by the API
    rfi_id     text,
    PRIMARY KEY (run_id, id),
    UNIQUE (run_id, check_id)
);

-- ---------- Human review ----------

CREATE TABLE IF NOT EXISTS reviews (
    id                    bigserial PRIMARY KEY,
    session_id            text,                       -- NULL = seed review visible to everyone
    finding_id            text NOT NULL,
    check_id              text NOT NULL,
    action                text NOT NULL CHECK (action IN ('accept', 'reject', 'correct')),
    corrected_result      text CHECK (corrected_result IN ('fail', 'conflict', 'missing_evidence', 'pass')),
    reason                text,
    evidence_fingerprint  text NOT NULL,              -- sha256 of the finding's cited paragraphs at review time
    golden_item_id        text,                       -- "corr-002" for reject and correct
    reviewer              text NOT NULL DEFAULT 'Demo reviewer',
    undo_token            text NOT NULL UNIQUE,
    reverted_at           timestamptz,
    created_at            timestamptz NOT NULL DEFAULT now(),
    CHECK (action = 'accept' OR (reason IS NOT NULL AND length(trim(reason)) > 0)),
    CHECK ((action = 'correct') = (corrected_result IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS reviews_live ON reviews (session_id, finding_id) WHERE reverted_at IS NULL;

-- ---------- Ask ----------

-- Every question asked, with what was retrieved and what was answered. Doubles as the
-- answer cache (same normalised question, same published run) and the rate-limit log.
CREATE TABLE IF NOT EXISTS asks (
    id             text PRIMARY KEY,
    session_id     text,
    run_id         text REFERENCES runs(id) ON DELETE SET NULL,
    question       text NOT NULL CHECK (length(question) BETWEEN 3 AND 500),
    question_norm  text NOT NULL,                     -- casefolded, punctuation and spaces collapsed
    route          text CHECK (route IN ('lookup', 'relationship', 'out_of_scope')),
    status         text NOT NULL CHECK (status IN ('answered', 'abstained', 'unavailable')),
    mode           text NOT NULL CHECK (mode IN ('replay', 'live', 'cache')),
    retrieved      jsonb NOT NULL DEFAULT '[]',       -- [{paragraph_id, vector_rank, keyword_rank, similarity, rrf}]
    response       jsonb NOT NULL,                    -- the AskResponse as served
    dropped        int NOT NULL DEFAULT 0,            -- sentences removed by verification
    cost_gbp       numeric(10, 5) NOT NULL DEFAULT 0,
    latency_ms     int NOT NULL,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS asks_cache ON asks (run_id, question_norm, created_at DESC);
CREATE INDEX IF NOT EXISTS asks_session_day ON asks (session_id, created_at);

-- ---------- Evals ----------

CREATE TABLE IF NOT EXISTS eval_runs (
    id                 bigserial PRIMARY KEY,
    session_id         text,                          -- NULL for CI and deploy runs
    run_id             text REFERENCES runs(id) ON DELETE SET NULL,
    state              text NOT NULL CHECK (state IN ('running', 'passing', 'failing', 'error')),
    score              numeric(5, 4),
    gate               numeric(5, 4) NOT NULL,
    metrics            jsonb NOT NULL DEFAULT '{}',
    golden_hash        text NOT NULL,                 -- hash of the golden items evaluated; "stale" = current hash differs
    golden_count       int NOT NULL,
    corrections_held   int,
    corrections_total  int,
    citation_validity  numeric(5, 4),
    cost_gbp           numeric(10, 5),
    error              text,
    started_at         timestamptz NOT NULL DEFAULT now(),
    finished_at        timestamptz
);
CREATE INDEX IF NOT EXISTS eval_runs_latest ON eval_runs (session_id, started_at DESC);
