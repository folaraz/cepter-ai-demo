import { useRef, type KeyboardEvent, type PointerEvent } from 'react';
import { PANE_MAX, PANE_MIN, useActions, useStore } from '../state/store';

const STEP = 20;

/** Keyboard- and pointer-resizable split between the finding panel and the document. */
export function Separator() {
  const { state } = useStore();
  const { setLeftW } = useActions();
  const drag = useRef<{ x: number; w: number } | null>(null);

  const onKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft') setLeftW(state.leftW - STEP);
    else if (e.key === 'ArrowRight') setLeftW(state.leftW + STEP);
    else if (e.key === 'Home') setLeftW(PANE_MIN);
    else if (e.key === 'End') setLeftW(PANE_MAX);
    else return;
    e.preventDefault();
  };

  const onPointerDown = (e: PointerEvent<HTMLDivElement>) => {
    if (e.button !== 0) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = { x: e.clientX, w: state.leftW };
    e.currentTarget.focus();
  };
  const onPointerMove = (e: PointerEvent<HTMLDivElement>) => {
    if (drag.current) setLeftW(drag.current.w + e.clientX - drag.current.x);
  };
  const end = () => {
    drag.current = null;
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize evidence panes"
      aria-valuemin={PANE_MIN}
      aria-valuemax={PANE_MAX}
      aria-valuenow={state.leftW}
      tabIndex={0}
      className="flex w-[9px] shrink-0 cursor-col-resize touch-none items-center justify-center border-x border-hairline bg-canvas focus-visible:-outline-offset-2 max-md:hidden"
      onKeyDown={onKeyDown}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={end}
      onPointerCancel={end}
    >
      <span aria-hidden="true" className="h-8 w-[3px] rounded-[2px] bg-control" />
    </div>
  );
}
