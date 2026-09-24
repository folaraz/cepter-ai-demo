// The status vocabulary from DESIGN_HANDOFF.md. Every status is glyph + word + colour token.
import type { CheckResult, EvalState, QuoteStatus, ReviewState, Severity } from '../api/types';

export interface StatusDef {
  glyph: string;
  word: string;
  /** CSS custom property that carries the meaning colour. */
  color: string;
}

export const SEVERITY: Record<Severity, StatusDef> = {
  critical: { glyph: '◆', word: 'Critical', color: 'var(--critical)' },
  high: { glyph: '▲', word: 'High', color: 'var(--high)' },
  medium: { glyph: '●', word: 'Medium', color: 'var(--medium)' },
  low: { glyph: '○', word: 'Low', color: 'var(--low)' },
};

export const RESULT: Record<CheckResult, StatusDef> = {
  fail: { glyph: '✕', word: 'Fail', color: 'var(--critical)' },
  conflict: { glyph: '≠', word: 'Conflict', color: 'var(--conflict)' },
  missing_evidence: { glyph: '○', word: 'Missing evidence', color: 'var(--missing)' },
  pass: { glyph: '✓', word: 'Pass', color: 'var(--ok)' },
};

export const REVIEW: Record<ReviewState, StatusDef> = {
  ai_extracted: { glyph: '◇', word: 'AI-extracted', color: 'var(--body)' },
  needs_review: { glyph: '!', word: 'Needs review', color: 'var(--high)' },
  lawyer_verified: { glyph: '✓', word: 'Lawyer-verified', color: 'var(--ok)' },
  corrected: { glyph: '✎', word: 'Corrected', color: 'var(--missing)' },
  rejected: { glyph: '✕', word: 'Rejected', color: 'var(--muted)' },
};

export const QUOTE: Record<QuoteStatus, StatusDef & { note: string }> = {
  verified: {
    glyph: '✓',
    word: 'Verified quote',
    color: 'var(--ok)',
    note: 'Quote found verbatim in this paragraph by the verifier. Not model-asserted.',
  },
  corroborated: {
    glyph: '✓✓',
    word: 'Corroborated',
    color: 'var(--ok)',
    note: 'Same value found verbatim in two or more documents.',
  },
  conflict: {
    glyph: '≠',
    word: 'Conflicting value',
    color: 'var(--conflict)',
    note: 'Quote verified, but its value disagrees with another document.',
  },
};

export const EVAL: Record<EvalState, StatusDef> = {
  passing: { glyph: '✓', word: 'Passing', color: 'var(--ok)' },
  stale: { glyph: '!', word: 'Re-run needed', color: 'var(--high)' },
  running: { glyph: '◌', word: 'Running…', color: 'var(--body)' },
  failing: { glyph: '✕', word: 'Failing', color: 'var(--critical)' },
};

/** Order of the Correct form's result options. */
export const RESULT_ORDER: CheckResult[] = ['fail', 'conflict', 'missing_evidence', 'pass'];
