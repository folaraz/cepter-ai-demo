import type { KeyboardEvent } from 'react';
import type { Summary } from '../api/types';
import { RESULT, REVIEW, SEVERITY } from '../lib/status';
import { evidenceLine, rowNumber } from '../lib/format';
import { cn } from '../lib/cn';
import { useActions, useStore } from '../state/store';
import { Glyph, hit, Kbd, panel, ResultPill, Sk, Tag } from '../components/ui';

const COLS = 6;

// Columns: # 34 · Finding flex · Severity 96 · Result 158 · Evidence 136 · Review 144.
// Narrower screens drop Evidence and Review, then stack Severity and Result under the title.
const row = cn(
  'grid min-h-(--row-h) grid-cols-[34px_minmax(0,1fr)_96px_158px_136px_144px] items-center gap-x-4 border-t border-hairline px-5 py-3',
  'max-lg:grid-cols-[28px_minmax(0,1fr)_90px_150px] max-lg:[&>:nth-child(n+5)]:hidden',
  'max-md:grid-cols-[24px_minmax(0,1fr)] max-md:gap-y-2 max-md:[&>:nth-child(3)]:col-start-2 max-md:[&>:nth-child(4)]:col-start-2',
);
const headRow = cn(row, 'border-t-0 py-2.5 max-md:[&>:nth-child(n+3)]:hidden');

function GridHead() {
  return (
    <div role="row" aria-rowindex={1} className={headRow}>
      <span role="columnheader" className="t-label">#</span>
      <span role="columnheader" className="t-label">Finding</span>
      <span role="columnheader" className="t-label" aria-sort="descending">
        Severity <span aria-hidden="true">↓</span>
      </span>
      <span role="columnheader" className="t-label">Result</span>
      <span role="columnheader" className="t-label">Evidence</span>
      <span role="columnheader" className="t-label">Review</span>
    </div>
  );
}

function SectionHead() {
  return (
    <div className="flex items-baseline justify-between gap-4">
      <h2 id="reg-h" className="t-label">
        Findings · sorted by severity
      </h2>
      <span aria-hidden="true" className="flex items-center gap-1.5 text-sm text-muted max-md:hidden">
        <Kbd>J</Kbd>
        <Kbd>K</Kbd> move <Kbd>↵</Kbd> evidence <Kbd>A</Kbd> accept <Kbd>C</Kbd> correct
      </span>
    </div>
  );
}

function PassedList({ summary, id }: { summary: Summary; id?: string }) {
  return (
    <ul id={id} className="flex flex-col gap-1.5 pr-4 pb-3.5 pl-[86px] text-md text-body max-md:pl-[46px]">
      {summary.passed.map((p) => (
        <li key={p.check_id}>
          {p.title} <span className="t-ref text-muted">{p.check_id}</span>
        </li>
      ))}
    </ul>
  );
}

export function FindingsGrid({ summary }: { summary: Summary }) {
  const { state } = useStore();
  const { select, openEvidence, move, togglePassed } = useActions();
  const rows = summary.findings;

  const onKeyDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    switch (e.key) {
      case 'ArrowDown':
        move(1, { focusRow: true });
        break;
      case 'ArrowUp':
        move(-1, { focusRow: true });
        break;
      case 'Home':
        if (rows[0]) select(rows[0].id, { focusRow: true });
        break;
      case 'End':
        if (rows.length) select(rows[rows.length - 1].id, { focusRow: true });
        break;
      case 'Enter':
        openEvidence();
        break;
      default:
        return;
    }
    e.preventDefault();
  };

  if (rows.length === 0) {
    return (
      <section aria-labelledby="reg-h" className="flex flex-col gap-2.5">
        <SectionHead />
        <div className={cn(panel, 'flex flex-col gap-2.5 px-5 pt-4')}>
          <Tag def={RESULT.pass}>All {summary.run.checks_total} checks passed</Tag>
          <PassedList summary={summary} />
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="reg-h" className="flex flex-col gap-2.5">
      <SectionHead />
      <div className={cn(panel, 'overflow-hidden')}>
        <div role="grid" aria-label="Findings" aria-rowcount={rows.length + 1} aria-colcount={COLS} onKeyDown={onKeyDown}>
          <GridHead />
          {rows.map((f, i) => {
            const selected = f.id === state.selectedId;
            return (
              <div
                key={f.id}
                role="row"
                aria-rowindex={i + 2}
                aria-selected={selected}
                tabIndex={selected ? 0 : -1}
                data-focus={`row-${f.id}`}
                className={cn(
                  row,
                  'transition-[background-color] duration-100 hover:bg-surface-strong focus-visible:-outline-offset-2',
                  selected && 'bg-surface-strong shadow-[inset_2px_0_0_var(--ink)]',
                )}
                onClick={() => select(f.id)}
                onDoubleClick={() => openEvidence(f.id)}
                onFocus={() => {
                  if (!selected) select(f.id);
                }}
              >
                <span role="gridcell" className="t-ref text-muted">
                  {rowNumber(i)}
                </span>
                <span role="gridcell" className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-base leading-[1.35] font-medium">{f.title}</span>
                  <span className="truncate text-sm text-muted">
                    <span className="t-ref">{f.check_id}</span> · {f.source_titles.join(', ')}
                  </span>
                </span>
                <span role="gridcell">
                  <Tag def={SEVERITY[f.severity]} />
                </span>
                <span role="gridcell">
                  <ResultPill def={RESULT[f.result]} />
                </span>
                <span role="gridcell" className="text-sm text-body">
                  {evidenceLine(f.quote_count, f.gap_count)}
                </span>
                <span role="gridcell">
                  <Tag def={REVIEW[f.review]} />
                </span>
              </div>
            );
          })}
        </div>
        <button
          type="button"
          aria-expanded={state.showPassed}
          aria-controls="passed-list"
          className={cn(
            hit,
            'flex w-full items-center gap-2 border-t border-hairline bg-transparent py-3 pr-4 pl-[66px] text-left text-md text-ok focus-visible:-outline-offset-2 max-md:pl-5',
          )}
          onClick={togglePassed}
        >
          <Glyph>✓</Glyph>
          {summary.passed.length} checks passed · {state.showPassed ? 'hide' : 'show'}
        </button>
        {state.showPassed && <PassedList summary={summary} id="passed-list" />}
      </div>
    </section>
  );
}

/** Skeleton with the grid's real row height and columns, so nothing shifts when findings land. */
export function FindingsSkeleton() {
  const widths = ['86%', '68%', '78%', '72%', '64%'];
  return (
    <section aria-busy="true" aria-label="Loading findings" className="flex flex-col gap-2.5">
      <SectionHead />
      <div className={cn(panel, 'overflow-hidden')} aria-hidden="true">
        <div className={headRow}>
          {['#', 'Finding', 'Severity', 'Result', 'Evidence', 'Review'].map((h) => (
            <span key={h} className="t-label">
              {h}
            </span>
          ))}
        </div>
        {widths.map((w, i) => (
          <div key={i} className={row}>
            <Sk className="w-3.5" />
            <span className="flex min-w-0 flex-col gap-1.5">
              <Sk style={{ width: w }} />
              <Sk className="w-[40%]" />
            </span>
            <Sk className="w-14" />
            <Sk className="h-6 w-22 rounded-pill" />
            <Sk className="w-28" />
            <Sk className="w-24" />
          </div>
        ))}
        <div className="border-t border-hairline py-3 pr-4 pl-[66px]">
          <Sk className="w-40" />
        </div>
      </div>
    </section>
  );
}
