import { SEVERITY } from '../lib/status';
import { useActions, useStore, useSummary } from '../state/store';
import { findingName } from '../lib/format';
import { ArrowRight, Download } from 'lucide-react';
import { Button, Icon, panel, Sk, Tag, TextLink } from '../components/ui';
import { cn } from '../lib/cn';
import { pageClass, pageHeadClass } from './SummaryView';
import { ErrorNote } from '../components/ErrorNote';

const rfiRow = 'grid grid-cols-[76px_minmax(0,1fr)] gap-4 px-6 py-6 max-md:grid-cols-1 max-md:gap-2';

const NUMBER_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
const countWord = (n: number) => NUMBER_WORDS[n] ?? String(n);

export function RequestsView() {
  const { state } = useStore();
  const { openEvidence, exportRfi, loadRfi } = useActions();
  const r = state.rfi;
  const summary = useSummary();
  const findingTitle = (id: string) => summary?.findings.find((f) => f.id === id)?.title ?? findingName(id);
  const n = r.status === 'ready' ? r.data.length : 3;
  const none = r.status === 'ready' && n === 0;

  return (
    <div className={`${pageClass} gap-6`}>
      <div className={pageHeadClass}>
        <div className="flex max-w-[720px] flex-auto flex-col gap-3">
          <h1 className="t-display text-pretty focus:outline-none!" data-focus="rfi-heading" tabIndex={-1}>
            {none
              ? 'No questions for the seller.'
              : `${countWord(n)} ${n === 1 ? 'question' : 'questions'} for the seller, each tied to the issue it resolves.`}
          </h1>
          <p className="max-w-[600px] text-md text-muted">
            Each question uses standard wording, so the same gap always gets the same request. Download them to send to the seller.
          </p>
        </div>
        <Button
          tone="ink"
          // aria-disabled keeps the button focusable, so the click itself is guarded too.
          onClick={() => r.status === 'ready' && !none && exportRfi()}
          aria-disabled={r.status !== 'ready' || none}
        >
          <Icon icon={Download} size={15} />
          Download questions
        </Button>
      </div>

      {r.status === 'error' ? (
        <ErrorNote title="Couldn't load the seller questions." onRetry={loadRfi} />
      ) : none ? (
        <p data-part="rfi-empty" className={cn(panel, 'px-6 py-6 text-md text-body')}>
          No open requests: every check either passed or rests on facts already in the data room.
        </p>
      ) : (
        <ol role="list" aria-busy={r.status === 'loading'} className={cn(panel, 'divide-y divide-hairline overflow-hidden')}>
          {r.status === 'ready'
            ? r.data.map((rfi) => (
                <li key={rfi.id} data-part="rfi" className={rfiRow}>
                  <span className="pt-0.5">
                    <span className="inline-flex h-6 items-center rounded-pill border border-hairline px-2 text-xs font-medium text-body tabular-nums">
                      {rfi.id}
                    </span>
                  </span>
                  <div className="flex flex-col gap-2.5">
                    <div className="flex items-center gap-3.5 max-md:flex-wrap">
                      <h2 className="text-lg font-semibold">{rfi.title}</h2>
                      <Tag def={SEVERITY[rfi.severity]} />
                      <span className="grow" />
                      <TextLink onClick={() => openEvidence(rfi.finding_id)}>
                        View finding
                        <Icon icon={ArrowRight} size={14} />
                        <span className="sr-only"> for {rfi.title}</span>
                      </TextLink>
                    </div>
                    <p className="max-w-[680px] text-base leading-[1.6]">{rfi.request}</p>
                    <dl className="grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-1.5 border-t border-hairline pt-3 text-md text-body [&_dt]:text-muted">
                      <dt>Why</dt>
                      <dd>{rfi.why}</dd>
                      <dt>Documents</dt>
                      <dd>{rfi.documents_expected.join('; ')}.</dd>
                      <dt>Resolves</dt>
                      <dd className="text-ink">{findingTitle(rfi.finding_id)}</dd>
                    </dl>
                  </div>
                </li>
              ))
            : [0, 1, 2].map((i) => (
                <li key={i} className={rfiRow} aria-hidden="true">
                  <Sk className="w-11" />
                  <div className="flex flex-col gap-2.5">
                    <Sk className="h-[15px] w-[220px]" />
                    <Sk className="w-[80%]" />
                    <Sk className="w-[60%]" />
                  </div>
                </li>
              ))}
        </ol>
      )}
    </div>
  );
}
