import { useStore, useActions } from '../state/store';
import { formatRunTime } from '../lib/format';
import { FactsCard } from './FactsCard';
import { DatesCard } from './DatesCard';
import { FindingsGrid, FindingsSkeleton } from './FindingsGrid';
import { ErrorNote } from '../components/ErrorNote';
import { Sk } from '../components/ui';

/** Scrolling page body shared by Summary and Requests. */
export const pageClass =
  'flex grow flex-col overflow-y-auto px-10 pt-8 pb-12 *:shrink-0 max-md:px-5 max-md:pt-6 max-md:pb-10';

export const pageHeadClass = 'relative flex items-end justify-between gap-6 max-md:flex-col max-md:items-start';

export function SummaryView() {
  const { state } = useStore();
  const { loadSummary } = useActions();
  const s = state.summary;

  return (
    <div className={`${pageClass} gap-7 overflow-x-hidden`}>
      <div className={pageHeadClass}>
        {/* The one gradient in the product: a soft glow behind the headline only. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute top-[-162px] left-[33%] h-[300px] w-[620px] bg-[radial-gradient(closest-side,var(--orb),var(--orb-0))]"
        />
        <div className="relative flex max-w-[720px] flex-auto flex-col gap-2.5">
          <span className="t-label">01. Diligence summary</span>
          <h1 className="t-display text-pretty focus:outline-none" data-focus="summary-heading" tabIndex={-1}>
            {s.status === 'ready' ? s.data.headline : s.status === 'loading' ? <Sk className="mt-1.5 h-[34px] w-[90%]" /> : 'Diligence summary'}
          </h1>
        </div>
        {s.status === 'ready' && (
          <span className="relative whitespace-nowrap text-sm text-muted">
            {s.data.run.checks_total} checks · run {s.data.run.id} · {formatRunTime(s.data.run.at)}
          </span>
        )}
      </div>

      {s.status === 'error' ? (
        <ErrorNote title="Couldn't load findings." detail={s.error} onRetry={loadSummary} />
      ) : (
        <>
          <FactsCard summary={s.status === 'ready' ? s.data : null} />
          <DatesCard summary={s.status === 'ready' ? s.data : null} />
          {s.status === 'ready' ? <FindingsGrid summary={s.data} /> : <FindingsSkeleton />}
        </>
      )}
    </div>
  );
}
