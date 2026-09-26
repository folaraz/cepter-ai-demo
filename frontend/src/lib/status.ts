// Status vocabulary. Every status is glyph + word + colour token.
// Words are plain language for the reviewer: deal terms are fine, system terms are not.
import {
  Ban,
  CircleAlert,
  CircleCheck,
  CircleDashed,
  CircleX,
  Check,
  CheckCheck,
  Circle,
  Diamond,
  EqualNot,
  FileQuestionMark,
  LoaderCircle,
  Pencil,
  Triangle,
  type LucideIcon,
} from 'lucide-react';
import type { CheckResult, EvalState, QuoteStatus, ReviewState, Severity } from '../api/types';

export interface StatusDef {
  /** Decorative icon; the word next to it carries the meaning. */
  icon: LucideIcon;
  /** Solid shape (severity markers) rather than an outline icon. */
  filled?: boolean;
  /** Rotate continuously (in-progress states). */
  spin?: boolean;
  word: string;
  /** CSS custom property that carries the meaning colour. */
  color: string;
}

export const SEVERITY: Record<Severity, StatusDef> = {
  critical: { icon: Diamond, filled: true, word: 'Critical', color: 'var(--critical)' },
  high: { icon: Triangle, filled: true, word: 'High', color: 'var(--high)' },
  medium: { icon: Circle, filled: true, word: 'Medium', color: 'var(--medium)' },
  low: { icon: Circle, word: 'Low', color: 'var(--low)' },
};

export const RESULT: Record<CheckResult, StatusDef> = {
  fail: { icon: CircleX, word: 'Issue found', color: 'var(--critical)' },
  conflict: { icon: EqualNot, word: 'Documents disagree', color: 'var(--conflict)' },
  missing_evidence: { icon: FileQuestionMark, word: 'Document missing', color: 'var(--missing)' },
  pass: { icon: CircleCheck, word: 'No issue', color: 'var(--ok)' },
};

export const REVIEW: Record<ReviewState, StatusDef> = {
  ai_extracted: { icon: CircleDashed, word: 'Not reviewed', color: 'var(--body)' },
  needs_review: { icon: CircleAlert, word: 'Needs review', color: 'var(--high)' },
  lawyer_verified: { icon: CircleCheck, word: 'Confirmed', color: 'var(--ok)' },
  corrected: { icon: Pencil, word: 'Corrected', color: 'var(--missing)' },
  rejected: { icon: Ban, word: 'Dismissed', color: 'var(--muted)' },
};

export const QUOTE: Record<QuoteStatus, StatusDef & { note: string }> = {
  verified: {
    icon: Check,
    word: 'Exact quote',
    color: 'var(--ok)',
    note: 'Quoted word for word from this page and checked against the original.',
  },
  corroborated: {
    icon: CheckCheck,
    word: 'Found in 2+ documents',
    color: 'var(--ok)',
    note: 'The same figure appears word for word in two or more documents.',
  },
  conflict: {
    icon: EqualNot,
    word: 'Documents disagree',
    color: 'var(--conflict)',
    note: 'Quoted word for word, but another document gives a different figure.',
  },
};

export const EVAL: Record<EvalState, StatusDef> = {
  passing: { icon: CircleCheck, word: 'Up to date', color: 'var(--ok)' },
  stale: { icon: CircleAlert, word: 'Re-check needed', color: 'var(--high)' },
  running: { icon: LoaderCircle, spin: true, word: 'Checking…', color: 'var(--body)' },
  failing: { icon: CircleX, word: 'Problems found', color: 'var(--critical)' },
};

/** Order of the Correct form's result options. */
export const RESULT_ORDER: CheckResult[] = ['fail', 'conflict', 'missing_evidence', 'pass'];
