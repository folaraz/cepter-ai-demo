// DataRoom Lens data layer. One flag switches every call between in-memory fixtures
// (review and eval state kept here) and the FastAPI backend. Shapes follow ./types.ts.
import type {
  EvalStatus,
  Finding,
  FindingRow,
  ReviewRequest,
  ReviewResponse,
  Rfi,
  Summary,
} from './types';
import summaryFixture from './fixtures/summary.json';
import evalFixture from './fixtures/eval-latest.json';
import rfiFixture from './fixtures/rfi.json';
import f01 from './fixtures/findings/F-01.json';
import f02 from './fixtures/findings/F-02.json';
import f03 from './fixtures/findings/F-03.json';
import f04 from './fixtures/findings/F-04.json';
import f05 from './fixtures/findings/F-05.json';
import type { AskResponse, AskSuggestion } from './ask.types';
import askSuggestionsFixture from './fixtures/ask/suggestions.json';
import askA01 from './fixtures/ask/a01.json';
import askR01 from './fixtures/ask/r01.json';
import askR03 from './fixtures/ask/r03.json';
import askR04 from './fixtures/ask/r04.json';
import askX01 from './fixtures/ask/x01.json';
import askUnavailable from './fixtures/ask/unavailable.json';
import { rfiToMarkdown } from './markdown';
import type { components } from './schema';

/** Live responses are typed by the FastAPI schema; schema.check.ts proves it equals ./types. */
type Api = components['schemas'];

export const USE_FIXTURES = import.meta.env.VITE_USE_FIXTURES !== 'false';
const API_BASE = import.meta.env.VITE_API_BASE ?? '';

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
  }
}

// ---------------------------------------------------------------- fixture backend

const clone = <T,>(v: T): T => structuredClone(v);
const EVAL_RUN_MS = 1000;

interface UndoEntry {
  row: FindingRow;
  evalStatus: EvalStatus;
  goldenId: string | null;
}

class FixtureBackend {
  private summary: Summary;
  private findings: Record<string, Finding>;
  private evalStatus: EvalStatus;
  private undo = new Map<string, UndoEntry>();
  private undoSeq = 0;

  constructor() {
    this.summary = clone(summaryFixture) as Summary;
    this.evalStatus = clone(evalFixture) as EvalStatus;
    const list = [f01, f02, f03, f04, f05].map((f) => clone(f) as Finding);
    this.findings = Object.fromEntries(list.map((f) => [f.id, f]));
  }

  private row(id: string): FindingRow {
    const r = this.summary.findings.find((f) => f.id === id);
    if (!r) throw new ApiError(`Finding ${id} not found`, 404);
    return r;
  }

  private setRow(next: FindingRow) {
    this.summary.findings = this.summary.findings.map((f) => (f.id === next.id ? next : f));
    const detail = this.findings[next.id];
    if (detail) this.findings[next.id] = { ...detail, result: next.result, review: next.review };
  }

  getSummary(): Summary {
    return clone({ ...this.summary, eval: this.evalStatus });
  }

  getFinding(id: string): Finding {
    const f = this.findings[id];
    if (!f) throw new ApiError(`Finding ${id} not found`, 404);
    return clone({ ...f, ...this.row(id) });
  }

  postReview(id: string, req: ReviewRequest): ReviewResponse {
    const before = this.row(id);
    if (req.action !== 'accept' && !req.reason?.trim()) throw new ApiError('A reason is required', 422);
    if (req.action === 'correct' && !req.corrected_result) throw new ApiError('corrected_result is required', 422);

    const prevEval = clone(this.evalStatus);
    let next: FindingRow;
    let goldenId: string | null = null;

    if (req.action === 'accept') {
      next = { ...before, review: 'lawyer_verified' };
    } else {
      goldenId = `corr-${String(this.evalStatus.corrections_total + 1).padStart(3, '0')}`;
      next =
        req.action === 'correct'
          ? { ...before, review: 'corrected', result: req.corrected_result! }
          : { ...before, review: 'rejected' };
      this.evalStatus = {
        ...this.evalStatus,
        state: 'stale',
        golden_count: this.evalStatus.golden_count + 1,
        corrections_total: this.evalStatus.corrections_total + 1,
      };
    }
    this.setRow(next);
    const token = `undo-${++this.undoSeq}`;
    this.undo.set(token, { row: before, evalStatus: prevEval, goldenId });
    return { finding: clone(next), golden_item_id: goldenId, eval: clone(this.evalStatus), undo_token: token };
  }

  undoReview(token: string): FindingRow {
    const entry = this.undo.get(token);
    if (!entry) throw new ApiError('Nothing to undo', 404);
    this.undo.delete(token);
    this.setRow(entry.row);
    this.evalStatus = entry.evalStatus;
    return clone(entry.row);
  }

  getRfi(): Rfi[] {
    return clone(rfiFixture) as Rfi[];
  }

  startEval(): EvalStatus {
    this.evalStatus = { ...this.evalStatus, state: 'running' };
    return clone(this.evalStatus);
  }

  finishEval(): EvalStatus {
    this.evalStatus = {
      ...this.evalStatus,
      state: 'passing',
      corrections_held: this.evalStatus.corrections_total,
      last_run_at: new Date().toISOString(),
    };
    return clone(this.evalStatus);
  }

  getEvalLatest(): EvalStatus {
    return clone(this.evalStatus);
  }
}

let fixtures = new FixtureBackend();

/** Test hook: start again from the pristine fixtures. */
export function resetFixtures() {
  fixtures = new FixtureBackend();
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
/** Fixture reads resolve on the next tick so loading states render exactly as they will against the API. */
const fixture = async <T,>(fn: () => T): Promise<T> => {
  await Promise.resolve();
  return fn();
};

// ---------------------------------------------------------------- HTTP backend

async function http<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { Accept: 'application/json', ...(init?.json !== undefined ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    body: init?.json !== undefined ? JSON.stringify(init.json) : init?.body,
  });
  if (!res.ok) throw new ApiError(`${init?.method ?? 'GET'} ${path} failed (${res.status})`, res.status);
  const type = res.headers.get('content-type') ?? '';
  return (type.includes('application/json') ? res.json() : res.text()) as Promise<T>;
}

// ---------------------------------------------------------------- public API

export function getSummary(): Promise<Summary> {
  return USE_FIXTURES ? fixture(() => fixtures.getSummary()) : http<Api['Summary']>('/api/summary');
}

export function getFinding(id: string): Promise<Finding> {
  return USE_FIXTURES ? fixture(() => fixtures.getFinding(id)) : http<Api['Finding']>(`/api/findings/${encodeURIComponent(id)}`);
}

export function postReview(id: string, body: ReviewRequest): Promise<ReviewResponse> {
  return USE_FIXTURES
    ? fixture(() => fixtures.postReview(id, body))
    : http<Api['ReviewResponse']>(`/api/findings/${encodeURIComponent(id)}/review`, { method: 'POST', json: body });
}

export function undoReview(undoToken: string): Promise<FindingRow> {
  return USE_FIXTURES
    ? fixture(() => fixtures.undoReview(undoToken))
    : http<Api['FindingRow']>('/api/reviews/undo', { method: 'POST', json: { undo_token: undoToken } });
}

export function getRfi(): Promise<Rfi[]> {
  return USE_FIXTURES ? fixture(() => fixtures.getRfi()) : http<Api['Rfi'][]>('/api/rfi');
}

export async function getRfiMarkdown(): Promise<string> {
  if (!USE_FIXTURES) return http('/api/rfi.md', { headers: { Accept: 'text/markdown' } });
  const [rfis, summary] = await Promise.all([getRfi(), getSummary()]);
  return rfiToMarkdown(rfis, summary.asset.name);
}

export function getEvalLatest(): Promise<EvalStatus> {
  return USE_FIXTURES ? fixture(() => fixtures.getEvalLatest()) : http<Api['EvalStatus']>('/api/evals/latest');
}

/** Starts an eval run and resolves once it has finished (polls the API while it reports "running"). */
export async function runEval(): Promise<EvalStatus> {
  if (USE_FIXTURES) {
    fixtures.startEval();
    await sleep(EVAL_RUN_MS);
    return fixtures.finishEval();
  }
  let status = await http<Api['EvalStatus']>('/api/evals/run', { method: 'POST' });
  while (status.state === 'running') {
    await sleep(750);
    status = await getEvalLatest();
  }
  return status;
}

// ---------------------------------------------------------------- Ask

export const ASK_MIN = 3;
export const ASK_MAX = 500;

/** Casefold, strip punctuation, collapse spaces: the backend's cache key (SPEC C14 step 1). */
export const normaliseQuestion = (q: string) =>
  q
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, '')
    .replace(/\s+/g, ' ')
    .trim();

const ASK_FIXTURES: Record<string, AskResponse> = Object.fromEntries(
  ([askA01, askR01, askR03, askR04, askX01] as unknown as AskResponse[]).map((r) => [normaliseQuestion(r.question), r]),
);

let askDelayMs = 1500;
/** Tests only: extra fixture answers keyed by question, or a function to simulate failures. */
export const __askFixtureOverrides = new Map<string, AskResponse | (() => AskResponse)>();
/** Tests only: how long a fixture answer takes. */
export function __setAskDelay(ms: number) {
  askDelayMs = ms;
}

const abortError = () => new DOMException('The question was cancelled.', 'AbortError');

function wait(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(abortError());
    const t = setTimeout(resolve, ms);
    signal?.addEventListener(
      'abort',
      () => {
        clearTimeout(t);
        reject(abortError());
      },
      { once: true },
    );
  });
}

export function getAskSuggestions(): Promise<AskSuggestion[]> {
  return USE_FIXTURES ? fixture(() => clone(askSuggestionsFixture) as AskSuggestion[]) : http<Api['AskSuggestion'][]>('/api/ask/suggestions');
}

/**
 * Asks a question about the data room. Resolves with the whole, verified answer (never
 * streamed). Rejects with an AbortError if `signal` fires, or ApiError(400) outside 3–500 characters.
 */
export async function askQuestion(question: string, signal?: AbortSignal): Promise<AskResponse> {
  const q = question.trim();
  if (q.length < ASK_MIN || q.length > ASK_MAX) throw new ApiError('Questions need 3 to 500 characters.', 400);
  if (!USE_FIXTURES) return http<Api['AskResponse']>('/api/ask', { method: 'POST', json: { question: q }, signal });

  await wait(askDelayMs, signal);
  const key = normaliseQuestion(q);
  const override = __askFixtureOverrides.get(key);
  if (override) return clone(typeof override === 'function' ? override() : override);
  // Suggested questions replay their recordings; anything else mirrors the server default
  // (live Ask off), exactly as the backend would answer.
  const hit = ASK_FIXTURES[key];
  // Note: unavailable.json carries question: null; the contract types it as string, so fill it in.
  return clone(hit ?? { ...(askUnavailable as unknown as AskResponse), question: q });
}

