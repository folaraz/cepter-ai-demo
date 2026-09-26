// DataRoom Lens: Ask API contract. Add these to design/api/types.ts (or import this file
// next to it). Reuses QuoteEvidence from types.ts, so the Evidence view can open any
// answer citation exactly like a finding's source.
import type { QuoteEvidence } from "./types";

/** How the backend answered. */
export type AskRoute =
  | "lookup"        // hybrid retrieval over paragraphs, answer written by the model, then verified
  | "relationship"  // a fixed graph query, answer rendered from a template (no model wording)
  | "out_of_scope"; // not about this data room

/**
 * answered     at least one sentence survived verification
 * abstained    the data room does not answer the question (message says why)
 * unavailable  live questions are off or over their limit (message says so; suggest a suggested question)
 */
export type AskStatus = "answered" | "abstained" | "unavailable";

export interface AskRequest {
  question: string; // 3–500 characters
}

export interface AskSentence {
  text: string;
  /** Verified quotes. Every model-written sentence has at least one. */
  citations: QuoteEvidence[];
  /**
   * Set only on template sentences that state an absence ("No easement covers
   * Parcels 14–15"). An absence cannot be quoted, so it links to the check that
   * established it instead. Model-written sentences never carry this.
   */
  finding_id: string | null;
}

export interface AskResponse {
  id: string;
  question: string;
  route: AskRoute | null;          // null when unavailable
  status: AskStatus;
  sentences: AskSentence[];        // empty unless status = "answered"
  message: string | null;          // shown instead of sentences when abstained or unavailable
  related_finding_id: string | null;
  related_rfi_id: string | null;
  /** Sentences removed because a citation or a number/date in them failed verification. */
  dropped_sentences: number;
  mode: "replay" | "live" | "cache";
  latency_ms: number;
  cost_gbp: number;
}

export interface AskSuggestion {
  id: string;        // golden item id, e.g. "a01"
  question: string;
  route: AskRoute;   // lets the UI hint what kind of answer to expect
}

// ---------- Endpoints ----------
// POST /api/ask                -> AskResponse        (body: AskRequest)
//   400 if the question is outside 3–500 characters.
//   Suggested questions always work (replayed). Free-form questions need ASK_LIVE=true
//   on the server; otherwise status "unavailable".
// GET  /api/ask/suggestions    -> AskSuggestion[]
//
// Not streamed: sentences are verified before they are sent, so a partial answer would
// be an unverified answer. Show a pending state for ~2–4 s instead.
