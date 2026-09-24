import type { Finding, QuoteEvidence } from '../api/types';
import { QUOTE } from '../lib/status';
import { useActions } from '../state/store';
import { Button, Glyph, Sk } from '../components/ui';
import { cn } from '../lib/cn';

// White sheet, 1px hairline, radius 4, one shadow tier, 56x64 padding (see .paper in app.css).
const paper =
  'paper flex min-h-[640px] flex-col gap-4 rounded-[4px] border border-hairline bg-paper px-16 py-14 font-display text-lg leading-[1.7] font-normal tracking-none text-paper-ink shadow-lift max-md:min-h-0 max-md:px-7 max-md:py-8';

// The fixtures carry only the cited paragraph; these neutral lines stand in for the
// surrounding clauses so the page reads like a document (same text as the artboard).
const CONTEXT_BEFORE =
  'The following provisions apply for the duration of this agreement and bind the parties and their permitted successors and assigns.';
const CONTEXT_AFTER = 'Any variation of this agreement must be in writing and signed by or on behalf of each party.';

export function SourcePage({ finding, quotes, srcIdx }: { finding: Finding | null; quotes: QuoteEvidence[]; srcIdx: number }) {
  const { setSrc } = useActions();
  const src = quotes[srcIdx];
  const n = quotes.length;

  return (
    <section
      aria-label="Source document"
      className="flex min-h-0 min-w-0 grow flex-col gap-3.5 overflow-y-auto px-8 pt-4 pb-8 max-md:overflow-visible max-md:px-5"
    >
      <div data-part="source-toolbar" className="flex min-h-7 items-center gap-3 text-sm text-body">
        {src ? (
          <>
            <span className="font-medium text-ink">{src.file_name}</span>
            <span className="t-ref">{src.citation.paragraph_id}</span>
          </>
        ) : (
          <Sk className="w-[200px]" />
        )}
        <span className="grow" />
        {n > 0 && (
          <span className="t-ref" aria-live="polite">
            Source {srcIdx + 1} of {n}
          </span>
        )}
        <Button size="xs" disabled={n < 2} onClick={() => setSrc((srcIdx - 1 + n) % n)}>
          Previous
        </Button>
        <Button size="xs" disabled={n < 2} onClick={() => setSrc((srcIdx + 1) % n)}>
          Next source
        </Button>
      </div>

      {src ? (
        <DocumentPage key={`${finding?.id}-${srcIdx}`} src={src} />
      ) : finding ? (
        <article className={cn(paper, 'justify-center font-body text-md text-paper-muted')} aria-label="No quoted source">
          <p>This finding has no quoted source, only missing evidence. See the dashed card on the left.</p>
        </article>
      ) : (
        <article className={paper} aria-hidden="true">
          <Sk className="w-[40%] bg-paper-rule" />
          <Sk className="w-[90%] bg-paper-rule" />
          <Sk className="w-[84%] bg-paper-rule" />
        </article>
      )}
    </section>
  );
}

function DocumentPage({ src }: { src: QuoteEvidence }) {
  const v = QUOTE[src.status];
  const text = src.paragraph_text;
  const before = text.slice(0, src.quote_start);
  const quote = text.slice(src.quote_start, src.quote_end);
  const after = text.slice(src.quote_end);
  return (
    <article className={paper} aria-label={`${src.document_title}, page ${src.citation.page}. Cited passage highlighted.`}>
      <div className="flex justify-between font-mono text-2xs tracking-[0.06em] text-paper-muted uppercase">
        <span>{src.document_title}</span>
        <span>Page {src.citation.page}</span>
      </div>
      <p className="text-paper-muted">{CONTEXT_BEFORE}</p>
      <h3 className="mt-1.5 text-heading font-light tracking-tight">{src.heading}</h3>
      <p>
        {before}
        <mark className="rounded-[2px] bg-mark py-px text-paper-ink box-decoration-clone">{quote}</mark>
        {after}
      </p>
      <p className="text-paper-muted">{CONTEXT_AFTER}</p>
      <div className="mt-auto flex items-baseline gap-2 border-t border-paper-rule pt-3.5 font-body text-sm leading-normal text-paper-body">
        <Glyph style={{ color: v.color }}>{v.glyph}</Glyph>
        <span>
          {v.word}. {v.note}
        </span>
      </div>
    </article>
  );
}
