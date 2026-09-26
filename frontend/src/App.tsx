import { useEffect, useLayoutEffect } from 'react';
import { parseHash, toHash } from './lib/route';
import { useActions, useStore } from './state/store';
import { isTypingTarget } from './lib/keys';
import { TopBar } from './components/TopBar';
import { Sidebar } from './components/Sidebar';
import { Toast } from './components/Toast';
import { ShortcutsDialog } from './components/ShortcutsDialog';
import { SummaryView } from './views/SummaryView';
import { EvidenceView } from './views/EvidenceView';
import { RequestsView } from './views/RequestsView';
import { AskView } from './views/AskView';

// ---------------------------------------------------------------- location hash <-> view

function useHashSync() {
  const { state } = useStore();
  const { setView, select, openEvidence } = useActions();
  const ready = state.summary.status === 'ready';

  // Back / forward. The initial route is read before first render (main.tsx).
  useEffect(() => {
    const apply = () => {
      const route = parseHash(window.location.hash);
      if (!route) return;
      if (route.view === 'evidence') openEvidence(route.id);
      else {
        if (route.id) select(route.id);
        setView(route.view);
      }
    };
    window.addEventListener('popstate', apply);
    return () => window.removeEventListener('popstate', apply);
  }, [openEvidence, select, setView]);

  // Reflect state in the hash: a new history entry per view, replace for J/K.
  useEffect(() => {
    if (!ready) return;
    const next = toHash(state.view, state.selectedId);
    if (window.location.hash === next) return;
    const prev = parseHash(window.location.hash);
    if (prev && prev.view !== state.view) window.history.pushState(null, '', next);
    else window.history.replaceState(null, '', next);
  }, [ready, state.view, state.selectedId]);
}

// ---------------------------------------------------------------- global keyboard

function useShortcuts() {
  const { stateRef } = useStore();
  const actions = useActions();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) return;
      if (isTypingTarget(e.target)) return;
      const s = stateRef.current;
      // The dialog handles its own keys. Ask the DOM, not state: Chrome fires the dialog's
      // close event a moment after it closes, and a key pressed in between must still work.
      if (document.querySelector('dialog[open]')) return;
      const inGrid = e.target instanceof HTMLElement && !!e.target.closest('[role="grid"]');
      const key = e.key.length === 1 ? e.key.toLowerCase() : e.key;

      if (e.key === '?') {
        e.preventDefault();
        actions.setHelp(true);
        return;
      }
      if (e.key === '/') {
        // Focus the Ask input from anywhere (opens Ask if needed).
        e.preventDefault();
        if (s.view !== 'ask') actions.setView('ask');
        actions.focus('ask-input');
        return;
      }
      if (s.view === 'rfi' || s.view === 'ask' || s.summary.status !== 'ready') return;

      if (key === 'j' || (s.view === 'evidence' && key === 'ArrowDown' && !inGrid && isPlainTarget(e.target))) {
        e.preventDefault();
        actions.move(1, { focusRow: s.view === 'summary' });
      } else if (key === 'k' || (s.view === 'evidence' && key === 'ArrowUp' && !inGrid && isPlainTarget(e.target))) {
        e.preventDefault();
        actions.move(-1, { focusRow: s.view === 'summary' });
      } else if (key === 'a') {
        e.preventDefault();
        void actions.review('accept');
      } else if (key === 'c') {
        e.preventDefault();
        if (s.view === 'summary') actions.openEvidence(undefined, 'correct');
        else actions.setMode('correct');
      } else if (key === 'r' && s.view === 'evidence') {
        e.preventDefault();
        actions.setMode('reject');
      } else if (key === 'Escape' && s.view === 'evidence' && s.reviewMode !== 'idle') {
        e.preventDefault();
        actions.setMode('idle');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [actions, stateRef]);
}

/** Arrow keys on buttons, the separator etc. keep their native meaning; only the page body steps findings. */
function isPlainTarget(t: EventTarget | null) {
  return !(t instanceof HTMLElement) || t === document.body || t.tabIndex === -1;
}

// ---------------------------------------------------------------- focus requests

function useFocusRequests() {
  const { state } = useStore();
  // Layout effect: the target rendered in this same commit (e.g. a form that just opened).
  useLayoutEffect(() => {
    if (!state.focus) return;
    document.querySelector<HTMLElement>(`[data-focus="${state.focus.key}"]`)?.focus();
  }, [state.focus]);
}

export function App() {
  const { state } = useStore();
  const { loadSummary, loadRfi, loadAskSuggestions } = useActions();

  useEffect(() => {
    void loadSummary();
    void loadRfi();
    void loadAskSuggestions();
  }, [loadSummary, loadRfi, loadAskSuggestions]);

  useHashSync();
  useShortcuts();
  useFocusRequests();

  return (
    <div className="relative flex h-full flex-col bg-canvas text-ink max-md:h-auto max-md:min-h-full">
      <a
        href="#main"
        className="absolute -top-12 left-3 z-50 rounded-pill border border-control bg-surface px-4 py-2 text-md text-ink no-underline transition-[top] duration-120 focus:top-3" onClick={(e) => { e.preventDefault(); document.getElementById('main')?.focus(); }}>
        Skip to main content
      </a>
      <TopBar />
      <div className="flex min-h-0 grow max-md:flex-col">
        <Sidebar />
        <main id="main" tabIndex={-1} className="flex min-h-0 min-w-0 grow flex-col focus:outline-none!">
          {state.view === 'summary' && <SummaryView />}
          {state.view === 'evidence' && <EvidenceView />}
          {state.view === 'rfi' && <RequestsView />}
          {state.view === 'ask' && <AskView />}
        </main>
      </div>
      <Toast />
      <ShortcutsDialog />
    </div>
  );
}
