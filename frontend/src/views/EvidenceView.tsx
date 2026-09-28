import type { Finding, QuoteEvidence } from '@design/api/types';
import { QUOTE, RESULT, REVIEW, SEVERITY } from '../lib/status';
import { useActions, useStore, useSummary } from '../state/store';
import { FileQuestionMark } from 'lucide-react';
import { ArrowLeft, ChevronDown, ChevronUp } from 'lucide-react';
import { Button, Count, hit, Icon, IconButton, ResultPill, Sk, Tag } from '../components/ui';

const subhead = 'text-sm font-semibold text-ink';
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
          <EvidenceNav index={index} total={summary?.findings.length ?? 0} />
          {entry?.status === 'error' ? (
            <ErrorNote title="Couldn't load this finding." onRetry={() => id && loadFinding(id, true)} />
          ) : finding ? (
            <FindingDetail finding={finding} num={index >= 0 ? index + 1 : null} srcIdx={srcIdx} />
          ) : (
            <FindingSkeleton />
          )}
        </div>
        {/* A passed check opened from a key fact is read-only: only flagged findings are reviewed. */}
        {finding && index >= 0 && <ReviewFooter key={finding.id} finding={finding} />}
      </section>
      <Separator />
      <SourcePage finding={finding} quotes={quotes} srcIdx={srcIdx} />
    </div>
  );
}

function EvidenceNav({ index, total }: { index: number; total: number }) {
  const { setView, move } = useActions();
  return (
    <div className="flex items-center justify-between">
      <Button size="sm" className="pl-2.5" onClick={() => setView('summary')}>
        <Icon icon={ArrowLeft} size={14} />
        All findings
      </Button>
      <div className="flex items-center gap-2">
        {total > 0 && index >= 0 && (
          <span className="text-sm text-muted tabular-nums">
            {index + 1} of {total}
          </span>
        )}
        <IconButton icon={ChevronUp} size="sm" aria-label="Previous finding" title="Previous finding (K)" disabled={index <= 0} onClick={() => move(-1)} />
        <IconButton icon={ChevronDown} size="sm" aria-label="Next finding" title="Next finding (J)" disabled={index >= total - 1} onClick={() => move(1)} />
      </div>
    </div>
  );
}

/** num: the finding's row number, or null for a passed check (not one of the flagged rows). */
function FindingDetail({ finding, num, srcIdx }: { finding: Finding; num: number | null; srcIdx: number }) {
  const { setSrc } = useActions();
  let q = -1;
  return (
    <>
      <div className="flex flex-col gap-3">
        <span className="text-sm font-medium text-muted">{num === null ? 'Passed check' : `Finding ${num}`}</span>
        <h1 id="ev-h" className="t-title text-pretty focus:outline-none!" data-focus="evidence-heading" tabIndex={-1}>
          {finding.title}
        </h1>
        <div data-part="finding-status" className="flex flex-wrap items-center gap-3.5">
          {num !== null && <Tag def={SEVERITY[finding.severity]} />}
          <ResultPill def={RESULT[finding.result]} />
          <Tag def={REVIEW[finding.review]} />
        </div>
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className={subhead}>Why it matters</h2>
        <p className="text-base leading-[1.6] text-pretty">{finding.why}</p>
      </div>
      <div className="flex flex-col gap-1.5">
        <h2 className={subhead}>How we reached this</h2>
        <p className="text-md leading-[1.6] text-pretty text-body">{finding.how}</p>
      </div>
      <div className="flex flex-col gap-2">
        <h2 className={cn(subhead, 'flex items-center gap-2')}>
          Sources <Count>{finding.evidence.length}</Count>
        </h2>
        <ol role="list" className="flex flex-col gap-1">
          {finding.evidence.map((ev, i) => {
            if (ev.kind === 'missing') {
              return (
                <li key={`m-${i}`}>
                  <div className="flex flex-col gap-[3px] rounded-inner border border-dashed border-missing bg-missing-soft px-3.5 py-3">
                    <Tag def={{ icon: FileQuestionMark, word: ev.label, color: 'var(--missing)' }} />
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
                    Page {ev.citation.page} · {ev.role}
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
