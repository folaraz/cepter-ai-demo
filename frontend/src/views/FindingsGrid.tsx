import type { KeyboardEvent } from 'react';
import type { Summary } from '@design/api/types';
import { RESULT, REVIEW, SEVERITY } from '../lib/status';
import { plural } from '../lib/format';
import { cn } from '../lib/cn';
import { useActions, useStore } from '../state/store';
import { ArrowDown, Check, ChevronDown, ChevronUp, CircleCheck, FileQuestionMark } from 'lucide-react';
import { hit, Icon, panel, ResultPill, SectionHeading, Sk, Tag } from '../components/ui';

const COLS = 6;

// Columns: # 34 · Finding flex · Severity 96 · Result 158 · Evidence 136 · Review 144.
// Narrower screens drop Evidence and Review, then stack Severity and Result under the title.
const row = cn(
  'grid min-h-(--row-h) grid-cols-[34px_minmax(0,1fr)_96px_158px_136px_144px] items-center gap-x-4 border-t border-hairline px-5 py-3',
  'max-lg:grid-cols-[28px_minmax(0,1fr)_90px_150px] max-lg:[&>:nth-child(n+5)]:hidden',
  'max-md:grid-cols-[24px_minmax(0,1fr)] max-md:gap-y-2 max-md:[&>:nth-child(3)]:col-start-2 max-md:[&>:nth-child(4)]:col-start-2',
);
const headRow = cn(row, 'min-h-0 border-t-0 bg-canvas-soft py-2.5 max-md:[&>:nth-child(n+3)]:hidden');
const th = 'text-sm font-medium text-muted';

function GridHead() {
  return (
    <div role="row" aria-rowindex={1} className={headRow}>
      <span role="columnheader" className={th}>#</span>
      <span role="columnheader" className={th}>Finding</span>
      <span role="columnheader" className={cn(th, 'inline-flex items-center gap-1')} aria-sort="descending">
        Severity <Icon icon={ArrowDown} size={12} />
      </span>
      <span role="columnheader" className={th}>Result</span>
      <span role="columnheader" className={th}>Sources</span>
      <span role="columnheader" className={th}>Review</span>
    </div>
  );
}

function SectionHead({ count }: { count?: number }) {
  return (
    <SectionHeading id="reg-h" title="Findings" count={count} description="Most serious first. Open a finding to see its sources." />
  );
}

function PassedList({ summary, id }: { summary: Summary; id?: string }) {
  return (
    <ul id={id} className="flex flex-col gap-2 pr-5 pb-4 pl-[74px] text-md text-body max-md:pl-5">
      {summary.passed.map((p) => (
        <li key={p.check_id} className="flex items-start gap-2">
          <Icon icon={Check} size={13} className="mt-1 text-ok" />
          {p.title}
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
          <Tag def={RESULT.pass}>All {summary.run.checks_total} checks passed with no issues</Tag>
          <PassedList summary={summary} />
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="reg-h" className="flex flex-col gap-2.5">
      <SectionHead count={rows.length} />
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
                <span role="gridcell" className="text-sm text-muted tabular-nums">
                  {i + 1}
                </span>
                <span role="gridcell" className="flex min-w-0 flex-col gap-0.5">
                  <span className="text-base leading-[1.35] font-medium">{f.title}</span>
                  <span className="truncate text-sm text-muted">From {f.source_titles.join(', ')}</span>
                </span>
                <span role="gridcell">
                  <Tag def={SEVERITY[f.severity]} />
                </span>
                <span role="gridcell">
                  <ResultPill def={RESULT[f.result]} />
                </span>
                <span role="gridcell" className="flex flex-col text-sm text-body">
                  <span>{plural(f.quote_count, 'quote')}</span>
                  {f.gap_count > 0 && (
                    <span className="inline-flex items-center gap-1 text-missing">
                      <Icon icon={FileQuestionMark} size={12} />
                      {f.gap_count} missing
                    </span>
                  )}
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
            'flex w-full items-center gap-2 border-t border-hairline bg-transparent py-3 pr-5 pl-[54px] text-left text-md focus-visible:-outline-offset-2 max-md:pl-5',
          )}
          onClick={togglePassed}
        >
          <Icon icon={CircleCheck} size={14} className="text-ok" />
          <span className="font-medium text-ink">{summary.passed.length} more checks passed</span>
          <span className="text-muted">with no issues</span>
          <span className="ml-auto inline-flex items-center gap-1 text-muted">
            {state.showPassed ? 'Hide' : 'Show'}
            <Icon icon={state.showPassed ? ChevronUp : ChevronDown} size={14} />
          </span>
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
          {['#', 'Finding', 'Severity', 'Result', 'Sources', 'Review'].map((h) => (
            <span key={h} className={th}>
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
