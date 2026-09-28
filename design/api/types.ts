// DataRoom Lens: API contract between the FastAPI backend and the React UI.
//
// Tonight the UI reads these shapes from ./fixtures. Tomorrow the backend returns
// exactly the same shapes, and the UI switches from fixtures to fetch() by changing
// one flag (see DESIGN_HANDOFF.md, "Data layer"). Once FastAPI exists, regenerate this
// file from its OpenAPI schema (openapi-typescript) and diff it against this one.

// ---------- Enums ----------

export type Severity = "critical" | "high" | "medium" | "low";

/** Outcome of a playbook check. "missing_evidence" is never shown as a fail. */
export type CheckResult = "fail" | "conflict" | "missing_evidence" | "pass";

/** Human review state of a finding. */
export type ReviewState =
  | "ai_extracted"
  | "needs_review"
  | "lawyer_verified"
  | "corrected"
  | "rejected";

/** Verifier status of a single quote. Unverified quotes never reach the UI as facts. */
export type QuoteStatus = "verified" | "corroborated" | "conflict";

export type EvalState = "passing" | "stale" | "running" | "failing";

// ---------- Evidence ----------

export interface Citation {
  document_id: string; // "grid_offer"
  paragraph_id: string; // "grid_offer:p2:¶3" (stable across runs)
  page: number;
  quote: string; // verbatim substring of paragraph_text
}

/** A verified quote plus the full paragraph it came from, for highlighting. */
export interface QuoteEvidence {
  kind: "quote";
  citation: Citation;
  document_title: string; // "Grid connection offer"
  file_name: string; // "grid_offer.pdf"
  role: string; // why this source matters, e.g. "connection date"
  heading: string; // clause heading shown above the paragraph
  paragraph_text: string;
  quote_start: number; // character offset of quote within paragraph_text
  quote_end: number; // exclusive
  status: QuoteStatus;
}

/** Evidence a check expected but could not find. Rendered as a dashed card. */
export interface MissingEvidence {
  kind: "missing";
  label: string; // "Deed of easement, Parcels 14–15"
  note: string;
  expected_by: string; // check_id
  rfi_id: string | null;
}

export type Evidence = QuoteEvidence | MissingEvidence;

// ---------- Findings ----------

export interface FindingRow {
  id: string; // "F-01"
  check_id: string; // "cable_route_rights"
  title: string;
  severity: Severity;
  result: CheckResult;
  review: ReviewState;
  quote_count: number;
  gap_count: number;
  source_titles: string[]; // for the one-line subtitle in the register
}

export interface Finding extends FindingRow {
  why: string; // "Why it matters"
  how: string; // "How the check decided"
  evidence: Evidence[];
}

// ---------- Summary ----------

export interface Fact {
  key: string; // "export_capacity"
  label: string;
  value: string; // display string, already formatted
  status: QuoteStatus;
  finding_id: string; // clicking the fact opens this finding's evidence
}

export interface DateMark {
  key: string;
  label: string;
  date: string; // ISO yyyy-mm-dd
  tone: "neutral" | "clash" | "warning";
  finding_id: string;
}

export interface DateClash {
  from_key: string; // "target_cod"
  to_key: string; // "grid_connection"
  days: number;
  label: string;
  finding_id: string;
}

export interface LongHorizonNote {
  text: string;
  flag: string;
  finding_id: string;
}

export interface DocumentSummary {
  id: string;
  title: string;
  file_name: string;
  pages: number;
}

export interface ExpectedDocument {
  label: string;
  expected_by: string;
  rfi_id: string;
  finding_id: string;
}

export interface EvalStatus {
  state: EvalState;
  score: number; // 0..1
  gate: number; // 0..1
  golden_count: number;
  corrections_held: number;
  corrections_total: number;
  citation_validity: number; // 0..1
  cost_gbp: number;
  last_run_at: string; // ISO datetime
}

export interface Summary {
  asset: { name: string; subtitle: string; synthetic: boolean };
  run: { id: string; at: string; checks_total: number };
  headline: string; // deterministic template, not free generation
  facts: Fact[];
  dates: DateMark[];
  date_window: { from: string; to: string };
  clash: DateClash | null; // null unless grid_before_cod flags (summary_view.yaml when_fails)
  long_horizon: LongHorizonNote | null; // null unless lease_covers_operating_life flags
  findings: FindingRow[]; // pre-sorted: severity desc, then id
  passed: { check_id: string; title: string }[];
  documents: DocumentSummary[];
  missing_documents: ExpectedDocument[];
  eval: EvalStatus;
}

// ---------- Review loop ----------

export interface ReviewRequest {
  action: "accept" | "reject" | "correct";
  corrected_result?: CheckResult; // required when action = "correct"
  reason?: string; // required for reject and correct
}

export interface ReviewResponse {
  finding: FindingRow;
  golden_item_id: string | null; // "corr-002" for reject/correct
  eval: EvalStatus; // state becomes "stale" after a new golden item
  undo_token: string;
}

// ---------- RFI ----------

export interface Rfi {
  id: string; // "RFI-01"
  finding_id: string;
  check_id: string;
  title: string;
  severity: Severity;
  request: string;
  why: string;
  documents_expected: string[];
}

// ---------- Endpoints ----------
// GET  /api/summary                     -> Summary
// GET  /api/findings/{id}               -> Finding
// POST /api/findings/{id}/review        -> ReviewResponse   (body: ReviewRequest)
// POST /api/reviews/undo                -> FindingRow       (body: { undo_token })
// GET  /api/rfi                         -> Rfi[]
// GET  /api/rfi.md                      -> text/markdown
// POST /api/evals/run                   -> EvalStatus       (may return state "running"; poll GET /api/evals/latest)
// GET  /api/evals/latest                -> EvalStatus
