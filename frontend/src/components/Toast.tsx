import { useEffect, useRef, useState } from 'react';
import { useActions, useStore } from '../state/store';

const AUTO_DISMISS_MS = 8000;

/** Bottom-centre ink pill. The live region stays mounted so screen readers announce each new message. */
export function Toast() {
  const { state } = useStore();
  const { undo, dismissToast } = useActions();
  const toast = state.toast;
  const [paused, setPaused] = useState(false);
  const remaining = useRef(AUTO_DISMISS_MS);
  const started = useRef(0);

  useEffect(() => {
    remaining.current = AUTO_DISMISS_MS;
    setPaused(false);
  }, [toast?.id]);

  useEffect(() => {
    if (!toast || paused) return;
    started.current = Date.now();
    const t = setTimeout(dismissToast, remaining.current);
    return () => {
      clearTimeout(t);
      remaining.current -= Date.now() - started.current;
    };
  }, [toast, paused, dismissToast]);

  return (
    <div role="status" aria-live="polite" className="pointer-events-none fixed bottom-5 left-1/2 z-40 -translate-x-1/2">
      {toast && (
        <div
          key={toast.id}
          data-part="toast"
          className="pointer-events-auto flex min-h-12 animate-rise items-center gap-3 whitespace-nowrap rounded-pill bg-primary py-0 pr-1.5 pl-5 text-md text-on-primary shadow-lift [&_:focus-visible]:outline-on-primary!"
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
          onFocus={() => setPaused(true)}
          onBlur={() => setPaused(false)}
        >
          <span>{toast.text}</span>
          {toast.undoToken && (
            <button type="button" className="h-9 rounded-pill border border-current bg-transparent px-4 text-md font-medium" onClick={undo}>
              Undo
            </button>
          )}
          <button type="button" className="size-9 rounded-pill border-none bg-transparent text-xl" aria-label="Dismiss" onClick={dismissToast}>
            <span aria-hidden="true">×</span>
          </button>
        </div>
      )}
    </div>
  );
}
