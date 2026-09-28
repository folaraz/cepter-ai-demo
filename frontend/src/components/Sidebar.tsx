import { FileQuestionMark, FileSearch, FileText, Files, LayoutList, MessageCircleQuestion, MessageSquareText, type LucideIcon } from 'lucide-react';
import { useActions, useStore, useSummary, type View } from '../state/store';
import { EVAL } from '../lib/status';
import { gbp, percent } from '../lib/format';
import { cn } from '../lib/cn';
import { Button, Count, Icon, Tag } from './ui';

const navItem =
  'grid h-9 w-full grid-cols-[24px_minmax(0,1fr)_auto] items-center rounded-inner border-none px-2.5 text-left text-md font-medium transition-[background-color] duration-120';

const groupHeading = 'px-2.5 text-sm font-semibold text-ink';
const subHeading = 'px-2.5 text-xs font-medium text-muted';

export function Sidebar() {
  const { state } = useStore();
  const summary = useSummary();
  const { setView, openEvidence, openDocument, runEval } = useActions();

  const nav: { view: View; icon: LucideIcon; label: string; count?: number }[] = [
    { view: 'summary', icon: LayoutList, label: 'Summary', count: summary?.findings.length },
    { view: 'evidence', icon: FileSearch, label: 'Evidence' },
    { view: 'documents', icon: Files, label: 'Documents', count: state.documents.status === 'ready' ? state.documents.data.length : undefined },
    { view: 'rfi', icon: MessageSquareText, label: 'Seller questions', count: state.rfi.status === 'ready' ? state.rfi.data.length : undefined },
    { view: 'ask', icon: MessageCircleQuestion, label: 'Ask' },
  ];

  const ev = summary?.eval;
  const running = ev?.state === 'running';

  return (
    <nav
      aria-label="Diligence"
      className="flex w-(--sidebar-w) shrink-0 flex-col gap-7 overflow-y-auto border-r border-hairline bg-canvas-soft px-3 pt-5 pb-4 max-md:w-auto max-md:overflow-visible max-md:border-r-0 max-md:border-b"
    >
      <div className="flex flex-col gap-0.5 px-2.5">
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
                className={cn(
                  navItem,
                  on ? 'bg-surface text-ink shadow-[0_0_0_1px_var(--hairline),0_1px_2px_rgba(0,0,0,0.04)]' : 'bg-transparent text-body hover:bg-surface-strong',
                )}
                onClick={() => (n.view === 'evidence' ? openEvidence() : n.view === 'documents' ? openDocument(null) : setView(n.view))}
              >
                <Icon icon={n.icon} size={15} className={on ? 'text-ink' : 'text-muted'} />
                <span>{n.label}</span>
                {n.count !== undefined ? <Count>{n.count}</Count> : <span />}
              </button>
            </li>
          );
        })}
      </ul>

      <section aria-labelledby="docs-h" className="flex flex-col gap-3">
        <h2 id="docs-h" className={groupHeading}>
          Documents
        </h2>
        <div className="flex flex-col">
        <h3 className={subHeading}>In the data room</h3>
        <ul role="list" className="pt-1">
          {summary?.documents.map((d) => {
            const on = state.view === 'documents' && state.docId === d.id;
            return (
              <li key={d.id}>
                <button
                  type="button"
                  aria-current={on ? 'page' : undefined}
                  title={`${d.title}, ${d.pages} ${d.pages === 1 ? 'page' : 'pages'}`}
                  onClick={() => openDocument(d.id)}
                  className={cn(
                    'grid h-[30px] w-full grid-cols-[24px_minmax(0,1fr)] items-center rounded-inner px-2.5 text-left text-md transition-[background-color] duration-120',
                    on ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--hairline)]' : 'text-body hover:bg-surface-strong',
                  )}
                >
                  <Icon icon={FileText} size={14} className={on ? 'text-ink' : 'text-muted'} />
                  <span className="truncate">{d.title}</span>
                </button>
              </li>
            );
          })}
        </ul>
        </div>

      {summary && summary.missing_documents.length > 0 && (
        <div className="flex flex-col gap-1">
          <h3 className={subHeading}>Missing</h3>
          {summary.missing_documents.map((m) => (
            <button
              key={m.label}
              type="button"
              className="grid w-full grid-cols-[24px_minmax(0,1fr)] items-start rounded-inner px-2.5 py-1.5 text-left text-md font-medium transition-[background-color] duration-120 hover:bg-surface-strong"
              onClick={() => openEvidence(m.finding_id)}
            >
              <Icon icon={FileQuestionMark} size={14} className="mt-0.5 text-missing" />
              <span className="flex flex-col gap-px">
                <span className="text-missing">{m.label}</span>
                <span className="text-xs font-normal text-muted">Requested from the seller</span>
              </span>
            </button>
          ))}
        </div>
      )}
      </section>

      <div className="grow max-md:hidden" />

      <section
        aria-labelledby="eval-h"
        data-part="eval-gate"
        className="flex flex-col gap-3 rounded-card border border-hairline bg-surface p-3.5"
      >
        <div className="flex items-center justify-between gap-2">
          <h2 id="eval-h" className="text-sm font-semibold text-ink">
            Accuracy check
          </h2>
          {ev && (
            <span role="status">
              <Tag def={EVAL[ev.state]} small />
            </span>
          )}
        </div>
        {ev && (
          <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1.5 text-sm [&_dd]:text-right [&_dd]:font-medium [&_dd]:tabular-nums [&_dt]:text-muted">
            <dt>Examples tested</dt>
            <dd>{ev.golden_count}</dd>
            <dt>Your corrections</dt>
            <dd>
              {ev.corrections_held} of {ev.corrections_total}
              {ev.corrections_held < ev.corrections_total ? ' re-checked' : ' hold'}
            </dd>
            <dt>Quote accuracy</dt>
            <dd>{percent(ev.citation_validity)}</dd>
            <dt>AI cost, this deal</dt>
            <dd>{gbp(ev.cost_gbp)}</dd>
          </dl>
        )}
        <Button size="eval" onClick={runEval} aria-disabled={!ev || running} data-focus="run-eval">
          {running ? 'Re-checking…' : 'Re-check now'}
        </Button>
      </section>
    </nav>
  );
}
