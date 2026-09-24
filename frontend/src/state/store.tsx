// One small store for the whole app: which view, which finding, review form state,
// loaded data and the toast. React context + useReducer; async work lives in useActions().
import { createContext, useCallback, useContext, useMemo, useReducer, useRef, type ReactNode } from 'react';
import * as api from '../api/client';
import type { CheckResult, EvalStatus, Finding, FindingRow, Rfi, Summary } from '../api/types';

export type View = 'summary' | 'evidence' | 'rfi';
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
};

type Action =
  | { type: 'summary'; value: Loadable<Summary> }
  | { type: 'finding'; id: string; value: Loadable<Finding> }
  | { type: 'rfi'; value: Loadable<Rfi[]> }
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
  | { type: 'focus'; key: string };

let nonce = 0;

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'summary': {
      const next = { ...state, summary: action.value };
      if (action.value.status === 'ready') {
        const rows = action.value.data.findings;
        // Keep a selection that came from the URL if it exists; otherwise start at the first row.
        if (!rows.some((f) => f.id === state.selectedId)) next.selectedId = rows[0]?.id ?? null;
      }
      return next;
    }
    case 'finding':
      return { ...state, findings: { ...state.findings, [action.id]: action.value } };
    case 'rfi':
      return { ...state, rfi: action.value };
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
    } catch (e) {
      dispatch({ type: 'summary', value: { status: 'error', error: message(e) } });
    }
  }, [dispatch, loadFinding]);

  const loadRfi = useCallback(async () => {
    dispatch({ type: 'rfi', value: { status: 'loading' } });
    try {
      dispatch({ type: 'rfi', value: { status: 'ready', data: await api.getRfi() } });
    } catch (e) {
      dispatch({ type: 'rfi', value: { status: 'error', error: message(e) } });
    }
  }, [dispatch]);

  const setView = useCallback((view: View) => dispatch({ type: 'view', view }), [dispatch]);

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
      dispatch({ type: 'saving', value: true });
      try {
        const res = await api.postReview(id, { action, ...payload });
        dispatch({ type: 'row', row: res.finding });
        dispatch({ type: 'eval', value: res.eval });
        dispatch({ type: 'mode', mode: 'idle' });
        const where = stateRef.current.view === 'summary' ? `row-${id}` : 'review-accept';
        const text =
          action === 'accept'
            ? `${id} accepted as lawyer-verified`
            : action === 'correct'
              ? `Saved as ${res.golden_item_id} in the golden set`
              : `${id} rejected · saved as ${res.golden_item_id}`;
        toast(text, { undoToken: res.undo_token, returnFocus: where });
        if (action !== 'accept') dispatch({ type: 'focus', key: where });
        return true;
      } catch (e) {
        toast(`Couldn't save the review. ${message(e)}`);
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
      toast(`Couldn't undo. ${message(e)}`);
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
        toast(`Eval passed · ${Math.round(done.score * 100)}% · ${all ? 'all corrections still hold' : `${done.corrections_held} of ${done.corrections_total} corrections hold`}`);
      } else {
        toast(`Eval failed · ${Math.round(done.score * 100)}% · below the ${Math.round(done.gate * 100)}% gate`);
      }
    } catch (e) {
      dispatch({ type: 'eval', value: s.summary.data.eval });
      toast(`Couldn't run the eval. ${message(e)}`);
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
      toast(`Exported ${n} requests as brackenfield-rfis.md`);
    } catch (e) {
      toast(`Couldn't export the requests. ${message(e)}`);
    }
  }, [stateRef, toast]);

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
    }),
    [loadSummary, loadFinding, loadRfi, setView, select, openEvidence, move, setMode, review, undo, runEval, exportRfi,
      setSrc, setLeftW, togglePassed, dismissToast, setHelp, focus],
  );
}

export type Actions = ReturnType<typeof useActions>;
