import type { ReactNode } from 'react';
import type { Finding, QuoteEvidence } from '@design/api/types';
import { QUOTE } from '../lib/status';
import { useActions, useSummary } from '../state/store';
import { BookOpenText, ChevronLeft, ChevronRight } from 'lucide-react';
import { Icon, IconButton, Sk, TextLink } from '../components/ui';
import { cn } from '../lib/cn';

// White sheet, 1px hairline, radius 4, one shadow tier, 56x64 padding (see .paper in app.css).
const paper =
  'paper flex flex-col gap-5 rounded-[4px] border border-hairline bg-paper px-16 pt-12 pb-10 font-display text-lg leading-[1.75] font-normal tracking-none text-paper-ink shadow-lift max-md:px-7 max-md:py-8';


/** The document viewer for a finding's sources (Evidence view). */
export function SourcePage({ finding, quotes, srcIdx }: { finding: Finding | null; quotes: QuoteEvidence[]; srcIdx: number }) {
  const { setSrc } = useActions();
  return (
    <SourcePane
      findingId={finding?.id}
      quotes={quotes}
      index={srcIdx}
      onIndex={setSrc}
      loading={!finding}
      resetKey={finding?.id}
      empty="There's nothing to quote for this finding yet: the document it needs is missing. See the dashed card on the left."
    />
  );
}

/**
 * Toolbar ("Source 2 of 3" with previous/next) and the paper page with the quote highlighted.
 * Shared by Evidence (a finding's sources) and Ask (an answer's citations).
 */
export function SourcePane({
  quotes,
  index,
  onIndex,
  loading,
  empty,
  resetKey,
  label = 'Source document',
  findingId,
}: {
  quotes: QuoteEvidence[];
  index: number;
  onIndex: (i: number) => void;
  loading?: boolean;
  /** Shown on the page when there are no quotes. */
  empty: ReactNode;
  /** Changes when the set of quotes belongs to something else (a different finding or answer). */
  resetKey?: string | number;
  label?: string;
  /** The finding these sources belong to; the reader then lights up that finding's note. */
  findingId?: string;
}) {
  const { openDocument } = useActions();
  const n = quotes.length;
  const i = Math.min(index, Math.max(0, n - 1));
  const src = quotes[i];

  return (
    <section
      aria-label={label}
      className="flex min-h-0 min-w-0 grow flex-col gap-3.5 overflow-y-auto px-8 pt-4 pb-8 max-md:overflow-visible max-md:px-5"
    >
      <div data-part="source-toolbar" className="flex min-h-7 items-center gap-3 text-sm text-body">
        {n > 0 ? (
          <span aria-live="polite" className="font-medium text-ink tabular-nums">
            Source {i + 1} of {n}
          </span>
        ) : loading ? (
          <Sk className="w-[120px]" />
        ) : null}
        <span className="grow" />
        {src && (
          <TextLink
            className="mr-2 text-sm"
            onClick={() => openDocument(src.citation.document_id, { paragraph: src.citation.paragraph_id, finding: findingId })}
          >
            <Icon icon={BookOpenText} size={14} />
            Open in document
          </TextLink>
        )}
        <div className="flex items-center gap-1.5">
          <IconButton icon={ChevronLeft} size="sm" aria-label="Previous source" disabled={n < 2} onClick={() => onIndex((i - 1 + n) % n)} />
          <IconButton icon={ChevronRight} size="sm" aria-label="Next source" disabled={n < 2} onClick={() => onIndex((i + 1) % n)} />
        </div>
      </div>

      {src ? (
        <DocumentPage key={`${resetKey}-${i}`} src={src} />
      ) : loading ? (
        <article className={paper} aria-hidden="true">
          <Sk className="w-[40%] bg-paper-rule" />
          <Sk className="w-[90%] bg-paper-rule" />
          <Sk className="w-[84%] bg-paper-rule" />
        </article>
      ) : (
        <article className={cn(paper, 'justify-center font-body text-md text-paper-muted')} aria-label="No quoted source">
          <p>{empty}</p>
        </article>
      )}
    </section>
  );
}

/** "Page 2 of 22" when the document's length is known, else "Page 2". */
function usePageLabel() {
  const summary = useSummary();
  return (src: QuoteEvidence) => {
    const total = summary?.documents.find((d) => d.id === src.citation.document_id)?.pages;
    return total ? `Page ${src.citation.page} of ${total}` : `Page ${src.citation.page}`;
  };
}

function DocumentPage({ src }: { src: QuoteEvidence }) {
  const pageLabel = usePageLabel();
  const v = QUOTE[src.status];
  const text = src.paragraph_text;
  const before = text.slice(0, src.quote_start);
  const quote = text.slice(src.quote_start, src.quote_end);
  const after = text.slice(src.quote_end);
  return (
    <article className={paper} aria-label={`${src.document_title}, page ${src.citation.page}. Cited passage highlighted.`}>
      <div className="flex items-baseline justify-between border-b border-paper-rule pb-3 font-body text-sm text-paper-muted">
        <span className="font-medium text-paper-body">{src.document_title}</span>
        <span className="tabular-nums">{pageLabel(src)}</span>
      </div>
      <div className="flex flex-col gap-3">
        <h3 className="text-heading font-normal tracking-tight">{src.heading}</h3>
        <p>
          {before}
          <mark className="rounded-[2px] bg-mark px-0.5 py-px text-paper-ink box-decoration-clone">{quote}</mark>
          {after}
        </p>
      </div>
      <div className="mt-2 flex items-start gap-2 rounded-inner bg-paper-note px-3.5 py-3 font-body text-sm leading-normal text-paper-body">
        <Icon icon={v.icon} size={14} className="mt-0.5" style={{ color: v.color }} />
        <span>
          {v.word}. {v.note}
        </span>
      </div>
    </article>
  );
}
