import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { ArrowLeft, CircleCheck } from 'lucide-react';
import type { DocumentDetail, DocumentListItem, DocumentNote, DocumentPage } from '@design/api/types';
import { QUOTE, RESULT } from '../lib/status';
import { findingName } from '../lib/format';
import { cn } from '../lib/cn';
import { useActions, useStore, useSummary } from '../state/store';
import { Button, Icon, panel, SectionHeading, Sk, Tag, TextLink } from '../components/ui';
import { ErrorNote } from '../components/ErrorNote';
import { pageClass, pageHeadClass } from './SummaryView';

const NUMBER_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten'];
const countWord = (n: number) => NUMBER_WORDS[n] ?? String(n);
const joinProse = (items: string[]) => (items.length <= 1 ? items.join('') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`);

export function DocumentsView() {
  const { state } = useStore();
  return state.docId ? <DocumentReader id={state.docId} /> : <DocumentsIndex />;
}

// ---------------------------------------------------------------- the data room

function DocumentsIndex() {
  const { state } = useStore();
  const summary = useSummary();
  const { openDocument, openEvidence, loadDocuments } = useActions();
  const docs = state.documents;
  const missing = summary?.missing_documents ?? [];
  const n = docs.status === 'ready' ? docs.data.length : 5;

  return (
    <div className={`${pageClass} gap-8`}>
      <div className={pageHeadClass}>
        <div className="flex max-w-[720px] flex-col gap-3">
          <h1 className="t-display text-pretty focus:outline-none!" data-focus="documents-heading" tabIndex={-1}>
            {`${countWord(n)} ${n === 1 ? 'document' : 'documents'} in the room. `}
            {missing.length === 0
              ? 'Nothing the checks need is missing.'
              : `${countWord(missing.length)} that the checks need ${missing.length === 1 ? 'is' : 'are'} missing.`}
          </h1>
          <p className="max-w-[600px] text-md text-muted">
            Open a document to read it page by page. Every passage a finding or key fact rests on is marked, with what was taken from it in the margin.
          </p>
        </div>
      </div>

      <section aria-labelledby="docs-in-h" className="flex flex-col gap-3">
        <SectionHeading id="docs-in-h" title="In the data room" count={docs.status === 'ready' ? docs.data.length : undefined} />
        {docs.status === 'error' ? (
          <ErrorNote title="Couldn't load the documents." onRetry={loadDocuments} />
        ) : (
          <ul role="list" aria-busy={docs.status === 'loading'} className={cn(panel, 'divide-y divide-hairline overflow-hidden')}>
            {docs.status === 'ready'
              ? docs.data.map((d) => (
                  <li key={d.id}>
                    <button
                      type="button"
                      data-part="document-row"
                      onClick={() => openDocument(d.id)}
                      className="grid w-full grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-5 px-6 py-5 text-left transition-[background-color] duration-120 hover:bg-surface-strong max-md:grid-cols-[40px_minmax(0,1fr)] max-md:px-4"
                    >
                      <Sheet pages={d.pages} />
                      <span className="flex min-w-0 flex-col gap-1">
                        <span className="text-lg font-medium text-ink">{d.title}</span>
                        {d.parties.length > 0 && <span className="text-md text-body">{partiesText(d)}</span>}
                        {d.date && (
                          <span className="text-sm text-muted">
                            {d.date.label} {d.date.value}
                          </span>
                        )}
                      </span>
                      <span className="flex flex-col items-end gap-1 text-right text-sm text-muted max-md:col-start-2 max-md:items-start max-md:text-left">
                        <span className="tabular-nums">
                          {d.pages} {d.pages === 1 ? 'page' : 'pages'}
                        </span>
                        <span>{findingsText(d, summary?.findings.map((f) => f.id) ?? [])}</span>
                      </span>
                    </button>
                  </li>
                ))
              : Array.from({ length: 5 }, (_, i) => (
                  <li key={i} className="grid grid-cols-[40px_minmax(0,1fr)] items-center gap-5 px-6 py-5" aria-hidden="true">
                    <Sk className="h-11 w-8" />
                    <span className="flex flex-col gap-2">
                      <Sk className="w-[40%]" />
                      <Sk className="w-[60%]" />
                    </span>
                  </li>
                ))}
          </ul>
        )}
      </section>

      {missing.length > 0 && (
        <section aria-labelledby="docs-missing-h" className="flex flex-col gap-3">
          <SectionHeading
            id="docs-missing-h"
            title="Missing"
            count={missing.length}
            description="Expected by a check but not in the room. Each one is a question for the seller."
          />
          <ul role="list" className="flex flex-col gap-2">
            {missing.map((m) => (
              <li key={m.label}>
                <button
                  type="button"
                  data-part="missing-row"
                  onClick={() => openEvidence(m.finding_id)}
                  className="grid w-full grid-cols-[40px_minmax(0,1fr)_auto] items-center gap-5 rounded-card border border-dashed border-missing bg-missing-soft px-6 py-4 text-left transition-[opacity] duration-120 hover:opacity-90 max-md:px-4"
                >
                  <Sheet pages={1} missing />
                  <span className="flex min-w-0 flex-col gap-1">
                    <span className="text-lg font-medium text-missing">{m.label}</span>
                    <span className="text-sm text-body">Requested from the seller</span>
                  </span>
                  <span className="text-sm text-muted">Needed by {findingName(m.finding_id)}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function partiesText(d: DocumentListItem) {
  return joinProse(d.parties.map((p) => `${p.name} (${p.role})`));
}

/** "Findings 1 and 4" for flagged findings; passed checks are counted, not numbered. */
function findingsText(d: DocumentListItem, flaggedIds: string[]) {
  const flagged = d.finding_ids.filter((id) => flaggedIds.includes(id));
  const passed = d.finding_ids.length - flagged.length;
  if (flagged.length > 0) {
    const nums = flagged.map((id) => String(Number(id.replace(/\D/g, ''))));
    return `${flagged.length === 1 ? 'Finding' : 'Findings'} ${joinProse(nums)}`;
  }
  if (passed > 0) return passed === 1 ? '1 passed check' : `${passed} passed checks`;
  return 'Not quoted by any check';
}

/** A small paper icon: a stack when the document has more than one page, dashed when it's missing. */
function Sheet({ pages, missing }: { pages: number; missing?: boolean }) {
  const sheet = cn(
    'absolute h-10 w-[30px] rounded-[3px] border',
    missing ? 'border-dashed border-missing bg-transparent' : 'border-control/45 bg-canvas-soft',
  );
  return (
    <span aria-hidden="true" className="relative block h-11 w-8">
      {!missing && pages > 1 && <span className={cn(sheet, 'top-1 left-1')} />}
      <span className={cn(sheet, 'top-0 left-0 flex flex-col gap-[3px] px-1.5 pt-2')}>
        {!missing &&
          [70, 90, 55].map((w) => <span key={w} className="h-px bg-control/45" style={{ width: `${w}%` }} />)}
      </span>
    </span>
  );
}

// ---------------------------------------------------------------- the reader

function DocumentReader({ id }: { id: string }) {
  const { state } = useStore();
  const { openDocument, loadDocument } = useActions();
  const entry = state.docs[id];
  const doc = entry?.status === 'ready' ? entry.data : null;
  // The title and details come from the list, so they show (and take focus) while the pages load.
  const listed = doc?.document ?? (state.documents.status === 'ready' ? state.documents.data.find((d) => d.id === id) : undefined);
  const scroller = useRef<HTMLDivElement>(null);
  const page = useCurrentPage(scroller, doc);

  const jump = (n: number) =>
    scroller.current?.querySelector(`[data-page="${n}"]`)?.scrollIntoView({ block: 'start', behavior: 'smooth' });

  return (
    <div ref={scroller} className="flex min-h-0 grow flex-col overflow-y-auto max-md:overflow-visible">
      <div className="sticky top-0 z-20 flex items-center gap-3 border-b border-hairline bg-canvas px-10 py-3 max-md:static max-md:px-5">
        <Button size="sm" className="pl-2.5" onClick={() => openDocument(null)}>
          <Icon icon={ArrowLeft} size={14} />
          All documents
        </Button>
        <span className="grow" />
        {doc && doc.pages.length > 1 && (
          <nav aria-label="Pages" className="flex items-center gap-1">
            <span className="mr-1 text-sm text-muted">Page</span>
            {doc.pages.map((p) => (
              <button
                key={p.number}
                type="button"
                aria-label={`Page ${p.number}`}
                aria-current={page === p.number ? 'page' : undefined}
                onClick={() => jump(p.number)}
                className={cn(
                  'size-7 rounded-pill text-sm tabular-nums transition-[background-color] duration-120',
                  page === p.number ? 'bg-surface font-medium text-ink shadow-[0_0_0_1px_var(--hairline)]' : 'text-body hover:bg-surface-strong',
                )}
              >
                {p.number}
              </button>
            ))}
          </nav>
        )}
      </div>

      {listed && <ReaderHeader d={listed} notes={listed.note_count} />}
      {entry?.status === 'error' ? (
        <div className="px-10 py-8 max-md:px-5">
          <ErrorNote title="Couldn't open this document." onRetry={() => loadDocument(id, true)} />
        </div>
      ) : doc ? (
        <Reading doc={doc} />
      ) : (
        <ReaderSkeleton />
      )}
    </div>
  );
}

/** The page most in view, for the page buttons. */
function useCurrentPage(scroller: React.RefObject<HTMLDivElement | null>, doc: DocumentDetail | null) {
  const [page, setPage] = useState(1);
  useEffect(() => {
    const root = scroller.current;
    if (!root || !doc || typeof IntersectionObserver === 'undefined') return;
    const seen = new Map<number, number>();
    const io = new IntersectionObserver(
      (items) => {
        items.forEach((i) => seen.set(Number((i.target as HTMLElement).dataset.page), i.intersectionRatio));
        const best = [...seen.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0];
        if (best && best[1] > 0) setPage(best[0]);
      },
      { root, threshold: [0, 0.25, 0.5, 0.75, 1] },
    );
    root.querySelectorAll('[data-page]').forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [scroller, doc]);
  return page;
}

function Reading({ doc }: { doc: DocumentDetail }) {
  const { state } = useStore();
  const { setActiveNote } = useActions();
  const [hover, setHover] = useState<string | null>(null);
  const lit = hover ?? state.activeNote;
  const d = doc.document;
  const total = d.pages;

  const notesByParagraph = useMemo(() => {
    const m = new Map<string, DocumentNote[]>();
    doc.notes.forEach((n) => m.set(n.paragraph_id, [...(m.get(n.paragraph_id) ?? []), n]));
    return m;
  }, [doc]);

  // Opened from a finding or an answer: light up that passage's note and bring it into view.
  const target = state.docTarget;
  useEffect(() => {
    if (!target?.paragraph) return;
    const inPara = doc.notes.filter((n) => n.paragraph_id === target.paragraph);
    const note = inPara.find((n) => target.finding && n.finding_ids.includes(target.finding)) ?? inPara[0];
    if (note) setActiveNote(note.id);
    document.querySelector(`[data-paragraph="${CSS.escape(target.paragraph)}"]`)?.scrollIntoView({ block: 'center' });
  }, [doc, target, setActiveNote]);

  // J/K: keep the lit note in view.
  useEffect(() => {
    if (!state.activeNote) return;
    const shown = [...document.querySelectorAll<HTMLElement>(`[data-note="${state.activeNote}"]`)].find((el) => el.offsetParent !== null);
    shown?.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }, [state.activeNote]);

  return (
    <div className="flex flex-col gap-8 px-10 pt-7 pb-16 max-md:px-5">

      {doc.pages.map((p) => (
        <PageSheet
          key={p.number}
          page={p}
          title={d.title}
          total={total}
          notesByParagraph={notesByParagraph}
          lit={lit}
          onHover={setHover}
          onPick={setActiveNote}
        />
      ))}
    </div>
  );
}

const GAP = 10; // px between stacked margin notes

/**
 * One page: the paper flows like a real page, and each paragraph's notes sit level with it
 * in the margin (like comments in a Word review), sliding down only to avoid overlapping.
 * Narrower than the margin needs, the notes fold in under their paragraph instead.
 */
function PageSheet({
  page,
  title,
  total,
  notesByParagraph,
  lit,
  onHover,
  onPick,
}: {
  page: DocumentPage;
  title: string;
  total: number;
  notesByParagraph: Map<string, DocumentNote[]>;
  lit: string | null;
  onHover: (id: string | null) => void;
  onPick: (id: string) => void;
}) {
  const ref = useRef<HTMLElement>(null);
  const [layout, setLayout] = useState<{ tops: Record<string, number>; height: number }>({ tops: {}, height: 0 });
  const groups = page.paragraphs.filter((q) => (notesByParagraph.get(q.id) ?? []).length > 0);

  useLayoutEffect(() => {
    const root = ref.current;
    if (!root) return;
    const place = () => {
      const base = root.getBoundingClientRect().top;
      const tops: Record<string, number> = {};
      let bottom = 0;
      root.querySelectorAll<HTMLElement>('[data-group]').forEach((g) => {
        const para = root.querySelector(`[data-paragraph="${CSS.escape(g.dataset.group!)}"]`);
        if (!para) return;
        const top = Math.max(para.getBoundingClientRect().top - base, bottom);
        tops[g.dataset.group!] = top;
        bottom = top + g.offsetHeight + GAP;
      });
      setLayout((prev) => (JSON.stringify(prev) === JSON.stringify({ tops, height: bottom }) ? prev : { tops, height: bottom }));
    };
    place();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(place);
    ro.observe(root);
    return () => ro.disconnect();
  }, [page, notesByParagraph]);

  return (
    <section
      ref={ref}
      data-page={page.number}
      aria-label={`Page ${page.number} of ${total}`}
      className="grid scroll-mt-16 grid-cols-[minmax(0,1fr)_17rem] items-start gap-x-8 max-lg:grid-cols-1"
    >
      <article className="paper flex flex-col gap-4 rounded-[4px] border border-hairline bg-paper px-16 pt-10 pb-12 font-display text-lg leading-[1.75] tracking-none text-paper-ink shadow-lift max-lg:px-7">
        <div className="mb-2 flex items-baseline justify-between border-b border-paper-rule pb-3 font-body text-sm text-paper-muted">
          <span className="font-medium text-paper-body">{title}</span>
          <span className="tabular-nums">
            Page {page.number} of {total}
          </span>
        </div>
        {page.paragraphs.map((para, i) => {
          const notes = notesByParagraph.get(para.id) ?? [];
          return (
            <div key={para.id} className="flex flex-col gap-2">
              {!!para.heading && para.heading !== page.paragraphs[i - 1]?.heading && (
                <h2 className="pt-2 text-heading font-normal tracking-tight">{para.heading}</h2>
              )}
              <p data-paragraph={para.id}>
                <Marked text={para.text} notes={notes} lit={lit} onHover={onHover} onPick={onPick} />
              </p>
              {notes.length > 0 && (
                <NoteCard notes={notes} lit={lit} onHover={onHover} className="mb-2 font-body lg:hidden" />
              )}
            </div>
          );
        })}
      </article>
      <aside aria-label={`Notes for page ${page.number}`} className="relative max-lg:hidden" style={{ minHeight: layout.height }}>
        {groups.map((q) => (
          <div
            key={q.id}
            data-group={q.id}
            className="absolute inset-x-0"
            style={{ top: layout.tops[q.id] ?? 0, visibility: q.id in layout.tops ? 'visible' : 'hidden' }}
          >
            <NoteCard notes={notesByParagraph.get(q.id) ?? []} lit={lit} onHover={onHover} />
          </div>
        ))}
      </aside>
    </section>
  );
}

function ReaderHeader({ d, notes }: { d: DocumentListItem; notes: number }) {
  return (
    <header className="flex max-w-[760px] flex-col gap-4 px-10 pt-7 max-md:px-5">
      <h1 className="t-title text-pretty focus:outline-none!" data-focus="document-heading" tabIndex={-1}>
        {d.title}
      </h1>
      <dl className="flex flex-wrap gap-x-10 gap-y-3 text-md">
        {d.parties.length > 0 && <Meta term="Parties">{joinProse(d.parties.map((p) => `${p.name} (${p.role})`))}</Meta>}
        {d.date && <Meta term={d.date.label}>{d.date.value}</Meta>}
        <Meta term="Length">
          {d.pages} {d.pages === 1 ? 'page' : 'pages'}
        </Meta>
      </dl>
      <p className="text-sm text-muted">
        {notes > 0
          ? 'Marked passages are quoted word for word. The margin shows what was taken from each one.'
          : 'Nothing in this document is quoted by a finding or key fact.'}
      </p>
    </header>
  );
}

function Meta({ term, children }: { term: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-sm text-muted">{term}</dt>
      <dd className="text-ink">{children}</dd>
    </div>
  );
}

/** The paragraph with each note's quote marked; overlapping quotes are split into segments. */
function Marked({
  text,
  notes,
  lit,
  onHover,
  onPick,
}: {
  text: string;
  notes: DocumentNote[];
  lit: string | null;
  onHover: (id: string | null) => void;
  onPick: (id: string) => void;
}) {
  if (notes.length === 0) return <>{text}</>;
  const cuts = [...new Set([0, text.length, ...notes.flatMap((n) => [n.quote_start, n.quote_end])])].sort((a, b) => a - b);
  return (
    <>
      {cuts.slice(0, -1).map((start, i) => {
        const end = cuts[i + 1];
        const on = notes.filter((n) => n.quote_start < end && start < n.quote_end);
        const piece = text.slice(start, end);
        if (on.length === 0) return <span key={start}>{piece}</span>;
        const active = on.some((n) => n.id === lit);
        return (
          <mark
            key={start}
            data-notes={on.map((n) => n.id).join(' ')}
            onMouseEnter={() => onHover(on[0].id)}
            onMouseLeave={() => onHover(null)}
            onClick={() => onPick(on[0].id)}
            className={cn(
              'cursor-pointer rounded-[2px] text-paper-ink box-decoration-clone transition-[background-color] duration-120',
              active ? 'bg-mark' : 'bg-mark/40',
            )}
          >
            {piece}
          </mark>
        );
      })}
    </>
  );
}

/** One card per paragraph, a row per statement taken from it. */
function NoteCard({
  notes,
  lit,
  onHover,
  className,
}: {
  notes: DocumentNote[];
  lit: string | null;
  onHover: (id: string | null) => void;
  className?: string;
}) {
  const on = notes.some((n) => n.id === lit);
  return (
    <ul
      role="list"
      className={cn(
        'divide-y divide-hairline overflow-hidden rounded-inner border bg-surface transition-[border-color] duration-120',
        on ? 'border-control' : 'border-hairline',
        className,
      )}
    >
      {notes.map((n) => (
        <li key={n.id}>
          <Note note={n} lit={lit === n.id} onHover={onHover} />
        </li>
      ))}
    </ul>
  );
}

function Note({ note, lit, onHover }: { note: DocumentNote; lit: boolean; onHover: (id: string | null) => void }) {
  const summary = useSummary();
  const { openEvidence } = useActions();
  const flagged = new Set(summary?.findings.map((f) => f.id) ?? []);
  const title = (id: string) => summary?.findings.find((f) => f.id === id)?.title;
  return (
    <div
      data-note={note.id}
      onMouseEnter={() => onHover(note.id)}
      onMouseLeave={() => onHover(null)}
      onFocus={() => onHover(note.id)}
      onBlur={() => onHover(null)}
      className={cn('flex flex-col gap-0.5 px-3.5 py-2.5 transition-[background-color] duration-120', lit && 'bg-surface-strong')}
    >
      <span className="text-sm text-muted">{note.label}</span>
      <span className="text-md font-medium wrap-anywhere text-ink">{note.value}</span>
      {/* Exact quotes are the norm (stated once above); only exceptions are tagged. */}
      {note.status !== 'verified' && <Tag def={QUOTE[note.status]} small />}
      {note.finding_ids.length > 0 && (
        <span className="flex flex-wrap gap-x-3">
          {note.finding_ids.map((id) =>
            flagged.has(id) ? (
              <FindingLink key={id} id={id} title={title(id)} onOpen={() => openEvidence(id)} />
            ) : (
              <TextLink key={id} className="text-sm" onClick={() => openEvidence(id)} title="Opens the check this passage passed">
                <Icon icon={CircleCheck} size={13} style={{ color: 'var(--ok)' }} />
                Passed check
              </TextLink>
            ),
          )}
        </span>
      )}
    </div>
  );
}

function FindingLink({ id, title, onOpen }: { id: string; title?: string; onOpen: () => void }) {
  const summary = useSummary();
  const row = summary?.findings.find((f) => f.id === id);
  const def = row ? RESULT[row.result] : null;
  return (
    <TextLink className="text-sm" onClick={onOpen} aria-label={title ? `${findingName(id)}: ${title}` : undefined} title={title}>
      {def && <Icon icon={def.icon} size={13} style={{ color: def.color }} />}
      {findingName(id)}
    </TextLink>
  );
}

function ReaderSkeleton() {
  return (
    <div className="flex flex-col gap-6 px-10 pt-8 max-md:px-5" aria-busy="true" aria-label="Loading document">
      <div className="paper flex max-w-[calc(100%-19rem)] flex-col gap-3 rounded-[4px] border border-hairline bg-paper px-16 py-12 max-lg:max-w-none">
        <Sk className="w-[35%] bg-paper-rule" />
        <Sk className="w-[90%] bg-paper-rule" />
        <Sk className="w-[80%] bg-paper-rule" />
      </div>
    </div>
  );
}
