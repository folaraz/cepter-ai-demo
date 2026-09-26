import type { Summary } from '../api/types';
import { QUOTE } from '../lib/status';
import { useActions } from '../state/store';
import { hit, panel, SectionHeading, Sk, Tag } from '../components/ui';
import { cn } from '../lib/cn';

// Cells sit on a 1px-gap grid over a hairline background, so dividers appear between
// cells at any column count (4 across, 2 across when narrow).
const cell = 'flex min-w-0 flex-col gap-1 bg-surface px-5 py-4 text-left focus-visible:-outline-offset-2';

export function FactsCard({ summary }: { summary: Summary | null }) {
  const { openEvidence } = useActions();
  return (
    <section aria-labelledby="facts-h" className={cn(panel, 'relative overflow-hidden')}>
      <SectionHeading
        id="facts-h"
        title="Key facts"
        description="Every value is quoted word for word from the documents."
        className="border-b border-hairline px-5 py-3.5"
      />
      <div className="grid grid-cols-4 gap-px bg-hairline max-lg:grid-cols-2">
        {summary
          ? summary.facts.map((f) => (
              <button
                key={f.key}
                type="button"
                className={cn(cell, hit)}
                onClick={() => openEvidence(f.finding_id)}
                aria-label={`${f.label}: ${f.value}. ${QUOTE[f.status].word}. Show the source`}
              >
                <span className="text-sm text-muted">{f.label}</span>
                <span className="text-lg font-medium wrap-anywhere">{f.value}</span>
                {/* Exact quotes are the norm (see heading); only exceptions are called out. */}
                {f.status === 'verified' ? <span className="h-[18px]" /> : <Tag def={QUOTE[f.status]} small />}
              </button>
            ))
          : Array.from({ length: 8 }, (_, i) => (
              <div key={i} className={cell} aria-hidden="true">
                <Sk className="w-[48%]" />
                <Sk className="h-[15px] w-[70%]" />
                <Sk className="w-[40%]" />
              </div>
            ))}
      </div>
    </section>
  );
}
