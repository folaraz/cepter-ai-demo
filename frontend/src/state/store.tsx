// One small store for the whole app: which view, which finding, review form state,
// loaded data and the toast. React context + useReducer; async work lives in useActions().
import { createContext, useCallback, useContext, useMemo, useReducer, useRef, type ReactNode } from 'react';
import * as api from '../api/client';
import type { CheckResult, DocumentDetail, DocumentListItem, EvalStatus, Finding, FindingRow, Rfi, Summary } from '@design/api/types';
import type { AskResponse, AskSuggestion } from '@design/api/ask.types';
import { findingName } from '../lib/format';

export type View = 'summary' | 'evidence' | 'documents' | 'rfi' | 'ask';
export type ReviewMode = 'idle' | 'reject' | 'correct';

export type Loadable<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: T };

export interface Toast {
  id: number;
  text: string;
  undoToken?: string;
  /** Where focus returns after Undo. */
  returnFocus?: string;
}

/** One question in this session's Ask history. Each keeps its own state. */
export type AskEntry = { key: number; question: string } & (
  | { status: 'pending'; phase: 'searching' | 'checking' }
  | { status: 'done'; response: AskResponse }
  | { status: 'error'; message: string }
);

export interface State {
  view: View;
  selectedId: string | null;
  srcIdx: number;
  reviewMode: ReviewMode;
  leftW: number;
  showPassed: boolean;
  summary: Loadable<Summary>;
  findings: Record<string, Loadable<Finding>>;
  rfi: Loadable<Rfi[]>;
  saving: boolean;
  toast: Toast | null;
  helpOpen: boolean;
  /** A request to move focus to the element with this data-focus key. */
  focus: { key: string; nonce: number } | null;
  askSuggestions: Loadable<AskSuggestion[]>;
  /** Newest first. */
  askEntries: AskEntry[];
  askDraft: string;
  /** Which answer's citation is open in the Ask document pane (index across the answer's citations). */
  askViewing: { entryKey: number; index: number } | null;
  /** Polite live-region text for the Ask view. */
  askAnnounce: string;
  documents: Loadable<DocumentListItem[]>;
  docs: Record<string, Loadable<DocumentDetail>>;
  /** The document open in the reader; null shows the list of documents. */
  docId: string | null;
  /** Where the reader was opened from: a paragraph to scroll to, and the finding that led there. */
  docTarget: DocTarget | null;
  /** The margin note that's lit up (J/K, hover or a deep link). */
  activeNote: string | null;
}

export interface DocTarget {
  paragraph?: string;
  finding?: string;
}

export const PANE_MIN = 400;
export const PANE_MAX = 760;

const initialState: State = {
  view: 'summary',
  selectedId: null,
  srcIdx: 0,
  reviewMode: 'idle',
  leftW: 500,
  showPassed: false,
  summary: { status: 'loading' },
  findings: {},
  rfi: { status: 'loading' },
  saving: false,
  toast: null,
  helpOpen: false,
  focus: null,
  askSuggestions: { status: 'loading' },
  askEntries: [],
  askDraft: '',
  askViewing: null,
  askAnnounce: '',
  documents: { status: 'loading' },
  docs: {},
  docId: null,
  docTarget: null,
  activeNote: null,
};

type Action =
  | { type: 'summary'; value: Loadable<Summary> }
  | { type: 'finding'; id: string; value: Loadable<Finding> }
  | { type: 'rfi'; value: Loadable<Rfi[]> }
  | { type: 'documents'; value: Loadable<DocumentListItem[]> }
  | { type: 'doc'; id: string; value: Loadable<DocumentDetail> }
  | { type: 'openDocument'; id: string | null; target: DocTarget | null }
  | { type: 'activeNote'; id: string | null }
  | { type: 'view'; view: View }
  | { type: 'select'; id: string; view?: View; mode?: ReviewMode }
  | { type: 'src'; idx: number }
  | { type: 'mode'; mode: ReviewMode }
  | { type: 'leftW'; width: number }
  | { type: 'togglePassed' }
  | { type: 'saving'; value: boolean }
  | { type: 'row'; row: FindingRow }
  | { type: 'eval'; value: EvalStatus }
  | { type: 'toast'; toast: Toast | null }
  | { type: 'help'; open: boolean }
  | { type: 'focus'; key: string }
  | { type: 'askSuggestions'; value: Loadable<AskSuggestion[]> }
  | { type: 'askEntry'; entry: AskEntry }
  | { type: 'askRemove'; key: number }
  | { type: 'askDraft'; value: string }
  | { type: 'askViewing'; value: State['askViewing'] }
  | { type: 'askAnnounce'; text: string };

let nonce = 0;

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'summary': {
      const next = { ...state, summary: action.value };
      if (action.value.status === 'ready') {
        const { findings: rows, facts, dates } = action.value.data;
        // Keep a selection that came from the URL if it exists (a flagged finding, or a passed
        // check a fact or date links to); otherwise start at the first row.
        const known = new Set([...rows.map((f) => f.id), ...facts.map((f) => f.finding_id), ...dates.map((d) => d.finding_id)]);
        if (!state.selectedId || !known.has(state.selectedId)) next.selectedId = rows[0]?.id ?? null;
      }
      return next;
    }
    case 'finding':
      return { ...state, findings: { ...state.findings, [action.id]: action.value } };
    case 'rfi':
      return { ...state, rfi: action.value };
    case 'documents':
      return { ...state, documents: action.value };
    case 'doc':
      return { ...state, docs: { ...state.docs, [action.id]: action.value } };
    case 'openDocument':
      return { ...state, view: 'documents', docId: action.id, docTarget: action.target, activeNote: null, reviewMode: 'idle' };
    case 'activeNote':
      return { ...state, activeNote: action.id };
    case 'view':
      return { ...state, view: action.view, reviewMode: action.view === 'evidence' ? state.reviewMode : 'idle' };
    case 'select': {
      const changed = action.id !== state.selectedId;
      return {
        ...state,
        selectedId: action.id,
        view: action.view ?? state.view,
        // Opening a finding always starts at source 1.
        srcIdx: changed || action.view === 'evidence' ? 0 : state.srcIdx,
        reviewMode: action.mode ?? (changed ? 'idle' : state.reviewMode),
      };
    }
    case 'src':
      return { ...state, srcIdx: action.idx };
    case 'mode':
      return { ...state, reviewMode: action.mode };
    case 'leftW':
      return { ...state, leftW: Math.max(PANE_MIN, Math.min(PANE_MAX, Math.round(action.width))) };
    case 'togglePassed':
      return { ...state, showPassed: !state.showPassed };
    case 'saving':
      return { ...state, saving: action.value };
    case 'row': {
      const findings = { ...state.findings };
      const cached = findings[action.row.id];
      if (cached?.status === 'ready') findings[action.row.id] = { status: 'ready', data: { ...cached.data, ...action.row } };
      if (state.summary.status !== 'ready') return { ...state, findings };
      const data = { ...state.summary.data, findings: state.summary.data.findings.map((f) => (f.id === action.row.id ? action.row : f)) };
      return { ...state, findings, summary: { status: 'ready', data } };
    }
    case 'eval':
      if (state.summary.status !== 'ready') return state;
      return { ...state, summary: { status: 'ready', data: { ...state.summary.data, eval: action.value } } };
    case 'toast':
      return { ...state, toast: action.toast };
    case 'help':
      return { ...state, helpOpen: action.open };
    case 'focus':
      return { ...state, focus: { key: action.key, nonce: ++nonce } };
    case 'askSuggestions':
      return { ...state, askSuggestions: action.value };
    case 'askEntry': {
      const exists = state.askEntries.some((e) => e.key === action.entry.key);
      const askEntries = exists
        ? state.askEntries.map((e) => (e.key === action.entry.key ? action.entry : e))
        : [action.entry, ...state.askEntries];
      return { ...state, askEntries };
    }
    case 'askRemove':
      return {
        ...state,
        askEntries: state.askEntries.filter((e) => e.key !== action.key),
        askViewing: state.askViewing?.entryKey === action.key ? null : state.askViewing,
      };
    case 'askDraft':
      return { ...state, askDraft: action.value };
    case 'askViewing':
      return { ...state, askViewing: action.value };
    case 'askAnnounce':
      return { ...state, askAnnounce: action.text };
  }
}

interface Ctx {
  state: State;
  dispatch: React.Dispatch<Action>;
  stateRef: React.MutableRefObject<State>;
}

const StoreContext = createContext<Ctx | null>(null);

export function StoreProvider({ children, initial }: { children: ReactNode; initial?: Partial<State> }) {
  const [state, dispatch] = useReducer(reducer, { ...initialState, ...initial });
  const stateRef = useRef(state);
  stateRef.current = state;
  const value = useMemo(() => ({ state, dispatch, stateRef }), [state]);
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore() {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore outside StoreProvider');
  return ctx;
}

// ---------------------------------------------------------------- derived helpers

export function useSummary(): Summary | null {
  const { state } = useStore();
  return state.summary.status === 'ready' ? state.summary.data : null;
}

export function useSelectedRow(): FindingRow | null {
  const { state } = useStore();
  const summary = useSummary();
  return summary?.findings.find((f) => f.id === state.selectedId) ?? null;
}

// ---------------------------------------------------------------- actions

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));
let toastSeq = 0;
let askSeq = 0;
/** In-flight Ask requests, so Cancel can abort them. Kept out of React state (not serialisable). */
const askControllers = new Map<number, AbortController>();

/** What the live region says when an answer arrives. */
function askAnnouncement(r: AskResponse): string {
  if (r.status !== 'answered') return r.message ?? 'No answer.';
  const n = r.sentences.length;
  return `Answer ready: ${n} ${n === 1 ? 'sentence' : 'sentences'}, each backed by the documents.`;
}

export function useActions() {
  const { dispatch, stateRef } = useStore();

  const toast = useCallback(
    (text: string, extra?: Omit<Toast, 'id' | 'text'>) => dispatch({ type: 'toast', toast: { id: ++toastSeq, text, ...extra } }),
    [dispatch],
  );

  const loadFinding = useCallback(
    async (id: string, force = false) => {
      const cur = stateRef.current.findings[id];
      if (!force && cur && cur.status !== 'error') return;
      dispatch({ type: 'finding', id, value: { status: 'loading' } });
      try {
        dispatch({ type: 'finding', id, value: { status: 'ready', data: await api.getFinding(id) } });
      } catch (e) {
        dispatch({ type: 'finding', id, value: { status: 'error', error: message(e) } });
      }
    },
    [dispatch, stateRef],
  );

  const loadSummary = useCallback(async () => {
    dispatch({ type: 'summary', value: { status: 'loading' } });
    try {
      const data = await api.getSummary();
      dispatch({ type: 'summary', value: { status: 'ready', data } });
      // Prefetch every finding so J/K in Evidence never waits.
      data.findings.forEach((f) => void loadFinding(f.id));
      // A passed check opened from the URL isn't a row, so load it too.
      const sel = stateRef.current.selectedId;
      if (sel && [...data.facts, ...data.dates].some((f) => f.finding_id === sel)) void loadFinding(sel);
    } catch (e) {
      dispatch({ type: 'summary', value: { status: 'error', error: message(e) } });
    }
  }, [dispatch, loadFinding, stateRef]);

  const loadRfi = useCallback(async () => {
    dispatch({ type: 'rfi', value: { status: 'loading' } });
    try {
      dispatch({ type: 'rfi', value: { status: 'ready', data: await api.getRfi() } });
    } catch (e) {
      dispatch({ type: 'rfi', value: { status: 'error', error: message(e) } });
    }
  }, [dispatch]);

  const setView = useCallback((view: View) => dispatch({ type: 'view', view }), [dispatch]);

  const loadDocuments = useCallback(async () => {
    dispatch({ type: 'documents', value: { status: 'loading' } });
    try {
      dispatch({ type: 'documents', value: { status: 'ready', data: await api.getDocuments() } });
    } catch (e) {
      dispatch({ type: 'documents', value: { status: 'error', error: message(e) } });
    }
  }, [dispatch]);

  const loadDocument = useCallback(
    async (id: string, force = false) => {
      const cur = stateRef.current.docs[id];
      if (!force && cur && cur.status !== 'error') return;
      dispatch({ type: 'doc', id, value: { status: 'loading' } });
      try {
        dispatch({ type: 'doc', id, value: { status: 'ready', data: await api.getDocument(id) } });
      } catch (e) {
        dispatch({ type: 'doc', id, value: { status: 'error', error: message(e) } });
      }
    },
    [dispatch, stateRef],
  );

  /** The list of documents (id null), or one document, optionally at a paragraph. */
  const openDocument = useCallback(
    (id: string | null, target: DocTarget | null = null) => {
      dispatch({ type: 'openDocument', id, target });
      if (id) void loadDocument(id);
      dispatch({ type: 'focus', key: id ? 'document-heading' : 'documents-heading' });
    },
    [dispatch, loadDocument],
  );

  const setActiveNote = useCallback((id: string | null) => dispatch({ type: 'activeNote', id }), [dispatch]);

  /** Step the lit-up margin note by delta (J/K in the reader). */
  const moveNote = useCallback(
    (delta: number) => {
      const s = stateRef.current;
      const doc = s.docId ? s.docs[s.docId] : undefined;
      if (doc?.status !== 'ready' || doc.data.notes.length === 0) return;
      const notes = doc.data.notes;
      const idx = notes.findIndex((n) => n.id === s.activeNote);
      const next = idx < 0 ? (delta > 0 ? 0 : notes.length - 1) : Math.max(0, Math.min(notes.length - 1, idx + delta));
      dispatch({ type: 'activeNote', id: notes[next].id });
    },
    [dispatch, stateRef],
  );

  const select = useCallback(
    (id: string, opts: { focusRow?: boolean } = {}) => {
      dispatch({ type: 'select', id });
      void loadFinding(id);
      if (opts.focusRow) dispatch({ type: 'focus', key: `row-${id}` });
    },
    [dispatch, loadFinding],
  );

  const openEvidence = useCallback(
    (id?: string, mode: ReviewMode = 'idle') => {
      const target = id ?? stateRef.current.selectedId;
      if (!target) return;
      dispatch({ type: 'select', id: target, view: 'evidence', mode });
      void loadFinding(target);
      if (mode === 'correct') dispatch({ type: 'focus', key: 'review-select' });
      else if (mode === 'reject') dispatch({ type: 'focus', key: 'review-reason' });
      else dispatch({ type: 'focus', key: 'evidence-heading' });
    },
    [dispatch, loadFinding, stateRef],
  );

  /** Step the selected finding by delta (J/K). */
  const move = useCallback(
    (delta: number, opts: { focusRow?: boolean } = {}) => {
      const s = stateRef.current;
      if (s.summary.status !== 'ready') return;
      const rows = s.summary.data.findings;
      const idx = rows.findIndex((f) => f.id === s.selectedId);
      const next = rows[Math.max(0, Math.min(rows.length - 1, idx + delta))];
      if (next && next.id !== s.selectedId) select(next.id, opts);
    },
    [select, stateRef],
  );

  const setMode = useCallback(
    (mode: ReviewMode) => {
      dispatch({ type: 'mode', mode });
      if (mode === 'correct') dispatch({ type: 'focus', key: 'review-select' });
      else if (mode === 'reject') dispatch({ type: 'focus', key: 'review-reason' });
    },
    [dispatch],
  );

  const review = useCallback(
    async (action: 'accept' | 'reject' | 'correct', payload: { reason?: string; corrected_result?: CheckResult } = {}) => {
      const s = stateRef.current;
      const id = s.selectedId;
      if (!id || s.saving) return false;
      // Only flagged findings are reviewed; a passed check opened from a fact is read-only.
      if (s.summary.status === 'ready' && !s.summary.data.findings.some((f) => f.id === id)) return false;
      dispatch({ type: 'saving', value: true });
      try {
        const res = await api.postReview(id, { action, ...payload });
        dispatch({ type: 'row', row: res.finding });
        dispatch({ type: 'eval', value: res.eval });
        dispatch({ type: 'mode', mode: 'idle' });
        const where = stateRef.current.view === 'summary' ? `row-${id}` : 'review-accept';
        const name = findingName(id);
        const text =
          action === 'accept'
            ? `${name} confirmed`
            : action === 'correct'
              ? `Correction saved. We'll re-check it on every run.`
              : `${name} dismissed. Your reason is saved.`;
        toast(text, { undoToken: res.undo_token, returnFocus: where });
        if (action !== 'accept') dispatch({ type: 'focus', key: where });
        return true;
      } catch (e) {
        console.error(e);
        toast("Couldn't save your review. Please try again.");
        return false;
      } finally {
        dispatch({ type: 'saving', value: false });
      }
    },
    [dispatch, stateRef, toast],
  );

  const undo = useCallback(async () => {
    const t = stateRef.current.toast;
    if (!t?.undoToken) return;
    try {
      const row = await api.undoReview(t.undoToken);
      dispatch({ type: 'row', row });
      dispatch({ type: 'eval', value: await api.getEvalLatest() });
      toast('Undone');
      if (t.returnFocus) dispatch({ type: 'focus', key: t.returnFocus });
    } catch (e) {
      console.error(e);
      toast("Couldn't undo. Please try again.");
    }
  }, [dispatch, stateRef, toast]);

  const runEval = useCallback(async () => {
    const s = stateRef.current;
    if (s.summary.status !== 'ready' || s.summary.data.eval.state === 'running') return;
    dispatch({ type: 'eval', value: { ...s.summary.data.eval, state: 'running' } });
    try {
      const done = await api.runEval();
      dispatch({ type: 'eval', value: done });
      if (done.state === 'passing') {
        const all = done.corrections_held === done.corrections_total;
        toast(all ? 'Re-check complete. All your corrections still hold.' : `Re-check complete. ${done.corrections_held} of ${done.corrections_total} corrections hold.`);
      } else {
        toast('Re-check found problems. Some results have changed since your corrections.');
      }
    } catch (e) {
      dispatch({ type: 'eval', value: s.summary.data.eval });
      console.error(e);
      toast("Couldn't run the re-check. Please try again.");
    }
  }, [dispatch, stateRef, toast]);

  const exportRfi = useCallback(async () => {
    try {
      const md = await api.getRfiMarkdown();
      const url = URL.createObjectURL(new Blob([md], { type: 'text/markdown;charset=utf-8' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'brackenfield-rfis.md';
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      const n = stateRef.current.rfi.status === 'ready' ? stateRef.current.rfi.data.length : 0;
      toast(`Downloaded ${n} seller questions`);
    } catch (e) {
      console.error(e);
      toast("Couldn't download the questions. Please try again.");
    }
  }, [stateRef, toast]);

  // ---------------------------------------------------------------- Ask

  const loadAskSuggestions = useCallback(async () => {
    dispatch({ type: 'askSuggestions', value: { status: 'loading' } });
    try {
      dispatch({ type: 'askSuggestions', value: { status: 'ready', data: await api.getAskSuggestions() } });
    } catch (e) {
      dispatch({ type: 'askSuggestions', value: { status: 'error', error: message(e) } });
    }
  }, [dispatch]);

  const setAskDraft = useCallback((value: string) => dispatch({ type: 'askDraft', value }), [dispatch]);

  /** Submits a question. The caller validates length; only one question is in flight at a time. */
  const ask = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (stateRef.current.askEntries.some((e) => e.status === 'pending')) return;
      const key = ++askSeq;
      const controller = new AbortController();
      askControllers.set(key, controller);
      dispatch({ type: 'askDraft', value: q });
      dispatch({ type: 'askEntry', entry: { key, question: q, status: 'pending', phase: 'searching' } });
      dispatch({ type: 'askAnnounce', text: 'Searching the documents…' });
      // Answers are verified before they're sent, so say what's happening after a moment.
      const phase = setTimeout(() => {
        dispatch({ type: 'askEntry', entry: { key, question: q, status: 'pending', phase: 'checking' } });
        dispatch({ type: 'askAnnounce', text: 'Checking every quote…' });
      }, 1000);
      try {
        const response = await api.askQuestion(q, controller.signal);
        dispatch({ type: 'askEntry', entry: { key, question: q, status: 'done', response } });
        dispatch({ type: 'askDraft', value: '' });
        const cited = response.status === 'answered' && response.sentences.some((s) => s.citations.length > 0);
        if (cited) dispatch({ type: 'askViewing', value: { entryKey: key, index: 0 } });
        dispatch({ type: 'askAnnounce', text: askAnnouncement(response) });
      } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') {
          dispatch({ type: 'askRemove', key });
          dispatch({ type: 'askAnnounce', text: 'Question cancelled.' });
          return;
        }
        console.error(e);
        const detail =
          e instanceof api.ApiError && e.status === 400 ? 'Questions need 3 to 500 characters.' : 'Check your connection, then try again.';
        dispatch({ type: 'askEntry', entry: { key, question: q, status: 'error', message: detail } });
        dispatch({ type: 'askAnnounce', text: `Couldn't get an answer. ${detail}` });
      } finally {
        clearTimeout(phase);
        askControllers.delete(key);
      }
    },
    [dispatch, stateRef],
  );

  const cancelAsk = useCallback(() => {
    askControllers.forEach((c) => c.abort());
  }, []);

  const retryAsk = useCallback(
    (key: number) => {
      const entry = stateRef.current.askEntries.find((e) => e.key === key);
      if (!entry) return;
      dispatch({ type: 'askRemove', key });
      void ask(entry.question);
    },
    [ask, dispatch, stateRef],
  );

  const viewAskSource = useCallback(
    (entryKey: number, index: number) => dispatch({ type: 'askViewing', value: { entryKey, index } }),
    [dispatch],
  );

  const setSrc = useCallback((idx: number) => dispatch({ type: 'src', idx }), [dispatch]);
  const setLeftW = useCallback((width: number) => dispatch({ type: 'leftW', width }), [dispatch]);
  const togglePassed = useCallback(() => dispatch({ type: 'togglePassed' }), [dispatch]);
  const dismissToast = useCallback(() => dispatch({ type: 'toast', toast: null }), [dispatch]);
  const setHelp = useCallback((open: boolean) => dispatch({ type: 'help', open }), [dispatch]);
  const focus = useCallback((key: string) => dispatch({ type: 'focus', key }), [dispatch]);

  return useMemo(
    () => ({
      loadSummary, loadFinding, loadRfi, setView, select, openEvidence, move, setMode, review, undo, runEval, exportRfi,
      setSrc, setLeftW, togglePassed, dismissToast, setHelp, focus,
      loadAskSuggestions, setAskDraft, ask, cancelAsk, retryAsk, viewAskSource,
      loadDocuments, loadDocument, openDocument, setActiveNote, moveNote,
    }),
    [loadSummary, loadFinding, loadRfi, setView, select, openEvidence, move, setMode, review, undo, runEval, exportRfi,
      setSrc, setLeftW, togglePassed, dismissToast, setHelp, focus,
      loadAskSuggestions, setAskDraft, ask, cancelAsk, retryAsk, viewAskSource,
      loadDocuments, loadDocument, openDocument, setActiveNote, moveNote],
  );
}

export type Actions = ReturnType<typeof useActions>;
