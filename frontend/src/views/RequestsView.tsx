import { SEVERITY } from '../lib/status';
import { useActions, useStore } from '../state/store';
import { Button, panel, Sk, Tag, TextLink } from '../components/ui';
import { cn } from '../lib/cn';
import { pageClass, pageHeadClass } from './SummaryView';
import { ErrorNote } from '../components/ErrorNote';

const rfiRow = 'grid grid-cols-[64px_minmax(0,1fr)] gap-4 px-6 py-5 max-md:grid-cols-1 max-md:gap-2';

const NUMBER_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
const countWord = (n: number) => NUMBER_WORDS[n] ?? String(n);

export function RequestsView() {
  const { state } = useStore();
  const { openEvidence, exportRfi, loadRfi } = useActions();
  const r = state.rfi;
  const n = r.status === 'ready' ? r.data.length : 3;

  return (
    <div className={`${pageClass} gap-6`}>
      <div className={pageHeadClass}>
        <div className="flex max-w-[700px] flex-auto flex-col gap-2.5">
          <span className="t-label">03. Requests for information</span>
          <h1 className="t-display text-pretty focus:outline-none" data-focus="rfi-heading" tabIndex={-1}>
            {countWord(n)} {n === 1 ? 'question' : 'questions'} for the seller, each tied to the check it unblocks.
          </h1>
          <p className="max-w-[600px] text-base text-body">
            Wording comes from the check definitions, not free generation, so the same gap always produces the same request.
          </p>
        </div>
        <Button tone="ink" onClick={exportRfi} aria-disabled={r.status !== 'ready'}>
          Export Markdown
        </Button>
      </div>

      {r.status === 'error' ? (
        <ErrorNote title="Couldn't load the requests." detail={r.error} onRetry={loadRfi} />
      ) : (
        <ol role="list" aria-busy={r.status === 'loading'} className={cn(panel, 'divide-y divide-hairline overflow-hidden')}>
          {r.status === 'ready'
            ? r.data.map((rfi) => (
                <li key={rfi.id} data-part="rfi" className={rfiRow}>
                  <span className="t-ref pt-0.5 text-sm text-muted">{rfi.id}</span>
                  <div className="flex flex-col gap-2.5">
                    <div className="flex items-center gap-3.5 max-md:flex-wrap">
                      <h2 className="text-lg font-semibold">{rfi.title}</h2>
                      <Tag def={SEVERITY[rfi.severity]} />
                      <span className="grow" />
                      <TextLink onClick={() => openEvidence(rfi.finding_id)}>
                        View finding <span aria-hidden="true">→</span>
                        <span className="sr-only"> {rfi.finding_id}</span>
                      </TextLink>
                    </div>
                    <p className="max-w-[680px] text-base leading-[1.6]">{rfi.request}</p>
                    <dl className="grid grid-cols-[96px_minmax(0,1fr)] gap-x-3 gap-y-1 text-md text-body [&_dt]:text-muted">
                      <dt>Why</dt>
                      <dd>{rfi.why}</dd>
                      <dt>Documents</dt>
                      <dd>{rfi.documents_expected.join('; ')}.</dd>
                      <dt>Unblocks</dt>
                      <dd className="t-ref text-sm text-ink">{rfi.check_id}</dd>
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
