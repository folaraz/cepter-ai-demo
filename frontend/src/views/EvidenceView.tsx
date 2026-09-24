import type { Finding, QuoteEvidence } from '../api/types';
import { QUOTE, RESULT, REVIEW, SEVERITY } from '../lib/status';
import { rowNumber } from '../lib/format';
import { useActions, useStore, useSummary } from '../state/store';
import { Button, hit, Kbd, ResultPill, Sk, Tag, TextLink } from '../components/ui';
import { cn } from '../lib/cn';
import { ErrorNote } from '../components/ErrorNote';
import { ReviewFooter } from './ReviewFooter';
import { Separator } from './Separator';
import { SourcePage } from './SourcePage';

export function EvidenceView() {
  const { state } = useStore();
  const summary = useSummary();
  const { loadFinding } = useActions();
  const id = state.selectedId;
  const entry = id ? state.findings[id] : undefined;
  const finding = entry?.status === 'ready' ? entry.data : null;
  const index = summary?.findings.findIndex((f) => f.id === id) ?? -1;
  const quotes = finding ? finding.evidence.filter((e): e is QuoteEvidence => e.kind === 'quote') : [];
  const srcIdx = Math.min(state.srcIdx, Math.max(0, quotes.length - 1));

  return (
    <div className="flex min-h-0 grow max-md:flex-col" style={{ ['--left-w' as string]: `${state.leftW}px` }}>
      <section aria-labelledby="ev-h" className="flex min-h-0 w-(--left-w) shrink-0 flex-col bg-surface max-md:w-auto">
        <div className="flex grow flex-col gap-5 overflow-y-auto px-7 py-6 max-md:overflow-visible">
          <EvidenceNav />
          {entry?.status === 'error' ? (
            <ErrorNote title="Couldn't load this finding." detail={entry.error} onRetry={() => id && loadFinding(id, true)} />
          ) : finding ? (
            <FindingDetail finding={finding} num={rowNumber(Math.max(0, index))} srcIdx={srcIdx} />
          ) : (
            <FindingSkeleton />
          )}
        </div>
        {finding && <ReviewFooter key={finding.id} finding={finding} />}
      </section>
      <Separator />
      <SourcePage finding={finding} quotes={quotes} srcIdx={srcIdx} />
    </div>
  );
}

function EvidenceNav() {
  const { setView, move } = useActions();
  return (
    <div className="flex items-center justify-between">
      <TextLink onClick={() => setView('summary')}>
        <span aria-hidden="true">←</span> Summary
      </TextLink>
      <span className="flex gap-1.5">
        <Button size="xs" className="px-2" aria-label="Previous finding" onClick={() => move(-1)}>
          <Kbd>K</Kbd>
        </Button>
        <Button size="xs" className="px-2" aria-label="Next finding" onClick={() => move(1)}>
          <Kbd>J</Kbd>
        </Button>
      </span>
    </div>
  );
}

function FindingDetail({ finding, num, srcIdx }: { finding: Finding; num: string; srcIdx: number }) {
  const { setSrc } = useActions();
  let q = -1;
  return (
    <>
      <div className="flex flex-col gap-2.5">
        <span className="t-label">
          {num}. {finding.check_id}
        </span>
        <h1 id="ev-h" className="t-title text-pretty focus:outline-none" data-focus="evidence-heading" tabIndex={-1}>
          {finding.title}
        </h1>
        <div data-part="finding-status" className="flex flex-wrap items-center gap-3.5">
          <Tag def={SEVERITY[finding.severity]} />
          <ResultPill def={RESULT[finding.result]} />
          <Tag def={REVIEW[finding.review]} />
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className="t-label">Why it matters</h2>
        <p className="text-base leading-[1.6] text-pretty">{finding.why}</p>
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className="t-label">How the check decided</h2>
        <p className="text-md leading-[1.6] text-pretty text-body">{finding.how}</p>
      </div>
      <div className="flex flex-col gap-2">
        <h2 className="t-label">Evidence · {finding.evidence.length} items</h2>
        <ol role="list" className="flex flex-col gap-1">
          {finding.evidence.map((ev, i) => {
            if (ev.kind === 'missing') {
              return (
                <li key={`m-${i}`}>
                  <div className="flex flex-col gap-[3px] rounded-inner border border-dashed border-missing bg-missing-soft px-3.5 py-3">
                    <Tag def={{ glyph: '○', word: ev.label, color: 'var(--missing)' }} />
                    <span className="text-sm text-body">{ev.note}</span>
                  </div>
                </li>
              );
            }
            const my = ++q;
            const v = QUOTE[ev.status];
            const on = my === srcIdx;
            return (
              <li key={ev.citation.paragraph_id + i}>
                <button
                  type="button"
                  aria-pressed={on}
                  onClick={() => setSrc(my)}
                  className={cn(
                    hit,
                    'flex w-full flex-col gap-[3px] rounded-inner border bg-surface px-3.5 py-3 text-left',
                    on ? 'border-ink' : 'border-hairline',
                  )}
                >
                  <span className="flex justify-between gap-2">
                    <span className="text-md font-medium">{ev.document_title}</span>
                    <Tag def={v} small />
                  </span>
                  <span className="text-sm text-muted">
                    <span className="t-ref">{ev.citation.paragraph_id}</span> · {ev.role}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
      </div>
    </>
  );
}

function FindingSkeleton() {
  return (
    <div className="flex flex-col gap-2.5" aria-busy="true" aria-label="Loading finding">
      <Sk className="w-[180px]" />
      <Sk className="mt-1 h-[22px] w-[90%]" />
      <Sk className="mt-1 h-[22px] w-[60%]" />
      <Sk className="mt-2 w-[260px]" />
    </div>
  );
}
