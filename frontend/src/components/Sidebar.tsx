import { useMemo } from 'react';
import { useActions, useSelectedRow, useStore, useSummary, type View } from '../state/store';
import { EVAL } from '../lib/status';
import { gbp, percent } from '../lib/format';
import { cn } from '../lib/cn';
import { Button, Glyph, Tag } from './ui';

const navItem =
  'grid h-9 w-full grid-cols-[30px_minmax(0,1fr)_auto] items-center rounded-pill border-none px-3.5 text-left text-md font-medium transition-[background-color] duration-120';

export function Sidebar() {
  const { state } = useStore();
  const summary = useSummary();
  const selected = useSelectedRow();
  const { setView, openEvidence, runEval } = useActions();

  const nav: { view: View; num: string; label: string; meta: string }[] = [
    { view: 'summary', num: '01.', label: 'Summary', meta: summary ? String(summary.findings.length) : '' },
    { view: 'evidence', num: '02.', label: 'Evidence', meta: state.selectedId ?? '' },
    { view: 'rfi', num: '03.', label: 'Requests', meta: state.rfi.status === 'ready' ? String(state.rfi.data.length) : '' },
  ];

  const cited = useMemo(() => new Set(selected?.source_titles ?? []), [selected]);
  const ev = summary?.eval;
  const running = ev?.state === 'running';

  return (
    <nav
      aria-label="Diligence"
      className="flex w-(--sidebar-w) shrink-0 flex-col gap-6 overflow-y-auto border-r border-hairline bg-canvas-soft px-3 pt-5 pb-4 max-md:w-auto max-md:overflow-visible max-md:border-r-0 max-md:border-b"
    >
      <div className="flex flex-col gap-1.5 px-2.5">
        <span className="t-label">Asset</span>
        <span className="text-lg leading-[1.3] font-semibold tracking-tight">{summary?.asset.name ?? ' '}</span>
        <span className="text-sm text-muted">{summary?.asset.subtitle ?? ' '}</span>
      </div>

      <ul role="list" className="flex flex-col gap-0.5">
        {nav.map((n) => {
          const on = state.view === n.view;
          return (
            <li key={n.view}>
              <button
                type="button"
                aria-current={on ? 'page' : undefined}
                className={cn(navItem, on ? 'bg-surface text-ink shadow-[0_0_0_1px_var(--hairline)]' : 'bg-transparent text-body hover:bg-surface-strong')}
                onClick={() => (n.view === 'evidence' ? openEvidence() : setView(n.view))}
              >
                <span className="t-ref text-muted">{n.num}</span>
                <span>{n.label}</span>
                <span className="t-ref text-muted">{n.meta}</span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="flex flex-col gap-0.5">
        <h2 className="t-label px-2.5 pb-2">Documents · {summary?.documents.length ?? 0}</h2>
        <ul role="list">
          {summary?.documents.map((d) => {
            const on = cited.has(d.title);
            return (
              <li
                key={d.id}
                className={cn('grid h-[30px] grid-cols-[30px_minmax(0,1fr)_auto] items-center px-2.5 text-md', on ? 'font-medium text-ink' : 'text-body')}
              >
                <Glyph className={on ? 'text-ink' : 'text-muted'}>{on ? '●' : '·'}</Glyph>
                <span className="truncate" title={d.file_name}>
                  {d.title}
                  {on && <span className="sr-only"> (cited by {selected?.id})</span>}
                </span>
                <span className="t-ref font-normal text-muted">{d.pages}p</span>
              </li>
            );
          })}
        </ul>
        {summary?.missing_documents.map((m) => (
          <button
            key={m.label}
            type="button"
            className="mt-1 grid w-full grid-cols-[30px_minmax(0,1fr)] items-start rounded-inner px-2.5 py-1.5 text-left text-md font-medium transition-[background-color] duration-120 hover:bg-surface-strong"
            onClick={() => openEvidence(m.finding_id)}
          >
            <Glyph className="pt-0.5 text-missing">○</Glyph>
            <span className="flex flex-col gap-px">
              <span className="text-missing">{m.label}</span>
              <span className="text-xs font-normal text-muted">Expected, not found · {m.rfi_id}</span>
            </span>
          </button>
        ))}
      </div>

      <div className="grow max-md:hidden" />

      <section aria-labelledby="eval-h" data-part="eval-gate" className="flex flex-col gap-2.5 border-t border-hairline px-2.5 pt-3">
        <div className="flex items-center justify-between">
          <h2 id="eval-h" className="t-label">
            Eval gate
          </h2>
          {ev && (
            <span role="status">
              <Tag def={EVAL[ev.state]} />
            </span>
          )}
        </div>
        {ev && (
          <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 text-sm [&_dd]:text-right [&_dd]:font-medium [&_dt]:text-muted">
            <dt>Golden set</dt>
            <dd>{ev.golden_count} items</dd>
            <dt>Corrections held</dt>
            <dd>
              {ev.corrections_held} of {ev.corrections_total}
              {ev.state === 'stale' || (running && ev.corrections_held < ev.corrections_total) ? ' checked' : ''}
            </dd>
            <dt>Citation validity</dt>
            <dd>{percent(ev.citation_validity)}</dd>
            <dt>Cost, this room</dt>
            <dd>{gbp(ev.cost_gbp)}</dd>
          </dl>
        )}
        <Button size="eval" onClick={runEval} aria-disabled={!ev || running} data-focus="run-eval">
          {running ? 'Running eval…' : 'Run eval'}
        </Button>
      </section>
    </nav>
  );
}
