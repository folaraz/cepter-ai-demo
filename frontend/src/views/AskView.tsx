// Ask: questions about the data room, answered only from the documents. Two panes like
// Evidence: the question and this session's answers on the left, the cited passage on the
// right, so every answer can be checked against its source without leaving the page.
import { useId, useMemo, useState, type FormEvent, type KeyboardEvent } from 'react';
import {
  CircleCheck,
  FileSearch,
  FileText,
  Info,
  LoaderCircle,
  MessageSquareText,
  Network,
  Search,
  CircleAlert,
  type LucideIcon,
} from 'lucide-react';
import type { AskResponse, AskRoute, AskSentence, AskSuggestion } from '../api/ask.types';
import type { QuoteEvidence } from '../api/types';
import { ASK_MAX, ASK_MIN } from '../api/client';
import { findingName, shortDocTitle } from '../lib/format';
import { cn } from '../lib/cn';
import { useActions, useStore, useSummary, type AskEntry } from '../state/store';
import { Button, hit, Icon, panel, TextLink } from '../components/ui';
import { Separator } from './Separator';
import { SourcePane } from './SourcePage';

const ROUTE: Record<AskRoute, { icon: LucideIcon; words: string }> = {
  lookup: { icon: Search, words: 'Looked up in the documents' },
  relationship: { icon: Network, words: 'From the asset model' },
  out_of_scope: { icon: Info, words: 'Outside these documents' },
};

/** Every citation of an answer, in reading order: the Ask document pane steps through these. */
const citationsOf = (r: AskResponse): QuoteEvidence[] => r.sentences.flatMap((s) => s.citations);

export function AskView() {
  const { state } = useStore();
  const { viewAskSource } = useActions();

  // The answer whose sources are open on the right.
  const viewing = useMemo(() => {
    const v = state.askViewing;
    const entry = v && state.askEntries.find((e) => e.key === v.entryKey);
    if (!v || !entry || entry.status !== 'done') return null;
    return { entryKey: entry.key, index: v.index, quotes: citationsOf(entry.response) };
  }, [state.askViewing, state.askEntries]);

  return (
    <div className="flex min-h-0 grow max-md:flex-col" style={{ ['--left-w' as string]: `${state.leftW}px` }}>
      <section aria-labelledby="ask-h" className="flex min-h-0 w-(--left-w) shrink-0 flex-col bg-surface max-md:w-auto">
        <div className="flex grow flex-col gap-6 overflow-y-auto px-7 py-6 max-md:overflow-visible">
          <div className="flex flex-col gap-2">
            <h1 id="ask-h" className="t-title text-pretty focus:outline-none!" data-focus="ask-heading" tabIndex={-1}>
              Ask about the data room
            </h1>
            <p className="text-md text-muted">
              Answers come only from the documents. Every sentence links to the passage it's based on.
            </p>
          </div>
          <AskForm />
          <AskHistory />
        </div>
      </section>
      <Separator />
      <SourcePane
        label="Answer sources"
        quotes={viewing?.quotes ?? []}
        index={viewing?.index ?? 0}
        onIndex={(i) => viewing && viewAskSource(viewing.entryKey, i)}
        resetKey={viewing?.entryKey}
        empty="Ask a question and the passage behind each answer opens here, highlighted."
      />
    </div>
  );
}

// ---------------------------------------------------------------- question form

function AskForm() {
  const { state } = useStore();
  const { ask, cancelAsk, setAskDraft } = useActions();
  const [invalid, setInvalid] = useState(false);
  const errId = useId();
  const hintId = useId();
  const pending = state.askEntries.some((e) => e.status === 'pending');

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    if (pending) return;
    const q = state.askDraft.trim();
    if (q.length < ASK_MIN || q.length > ASK_MAX) {
      setInvalid(true);
      return;
    }
    void ask(q);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    } else if (e.key === 'Escape' && pending) {
      e.preventDefault();
      cancelAsk();
    }
  };

  return (
    <form className="flex flex-col gap-2.5" onSubmit={submit} noValidate>
      <label htmlFor="ask-input" className="text-sm font-semibold text-ink">
        Your question
      </label>
      <textarea
        id="ask-input"
        data-focus="ask-input"
        rows={3}
        maxLength={ASK_MAX + 100}
        value={state.askDraft}
        placeholder="e.g. When does the lease end?"
        aria-invalid={invalid}
        aria-describedby={invalid ? `${errId} ${hintId}` : hintId}
        onChange={(e) => {
          setAskDraft(e.target.value);
          if (invalid) setInvalid(false);
        }}
        onKeyDown={onKeyDown}
        className="w-full resize-none rounded-input border border-control bg-surface px-3.5 py-3 text-base leading-normal text-ink aria-invalid:border-critical"
      />
      {invalid && (
        <span id={errId} className="inline-flex items-center gap-1.5 text-sm font-medium text-critical">
          <Icon icon={CircleAlert} size={13} />
          Questions need {ASK_MIN} to {ASK_MAX} characters.
        </span>
      )}
      <div className="flex items-center gap-3">
        <span id={hintId} className="text-sm text-muted">
          Enter to ask, Shift + Enter for a new line
        </span>
        <span className="grow" />
        <Button type="submit" tone="ink" aria-disabled={pending} className={pending ? 'opacity-50' : undefined}>
          Ask
        </Button>
      </div>
    </form>
  );
}

// ---------------------------------------------------------------- history

function AskHistory() {
  const { state } = useStore();
  const entries = state.askEntries;
  const latest = entries[0];
  // Suggestions before the first question, and again after an "unavailable" answer.
  const showSuggestions = !latest || (latest.status === 'done' && latest.response.status === 'unavailable');

  return (
    <>
      {/* Polite announcements: pending progress, then the outcome. Focus stays in the input. */}
      <p role="status" aria-live="polite" className="sr-only">
        {state.askAnnounce}
      </p>
      {showSuggestions && !latest && <Suggestions />}
      {entries.length > 0 && (
        <section aria-labelledby="ask-history-h" className="flex flex-col gap-3">
          <h2 id="ask-history-h" className="sr-only">
            Your questions
          </h2>
          <ol role="list" className="flex flex-col gap-3">
            {entries.map((e, i) => (
              <li key={e.key}>
                <EntryCard entry={e} />
                {i === 0 && showSuggestions && (
                  <div className="mt-3">
                    <Suggestions />
                  </div>
                )}
              </li>
            ))}
          </ol>
        </section>
      )}
    </>
  );
}

function Suggestions() {
  const { state } = useStore();
  const { ask, focus } = useActions();
  const s = state.askSuggestions;
  const pending = state.askEntries.some((e) => e.status === 'pending');
  if (s.status !== 'ready' || s.data.length === 0) return null;

  const pick = (q: AskSuggestion) => {
    if (pending) return;
    void ask(q.question);
    // The suggestion list may disappear once answered; keep focus in the input.
    focus('ask-input');
  };

  return (
    <section aria-labelledby="ask-suggest-h" className="flex flex-col gap-2">
      <h2 id="ask-suggest-h" className="text-sm font-semibold text-ink">
        Try a suggested question
      </h2>
      <ul role="list" className="flex flex-col gap-1.5">
        {s.data.map((q) => (
          <li key={q.id}>
            <button
              type="button"
              aria-disabled={pending}
              onClick={() => pick(q)}
              className={cn(
                hit,
                'flex min-h-10 w-full items-center gap-2.5 rounded-inner border border-hairline bg-surface px-3.5 py-2 text-left text-md text-ink',
              )}
            >
              <Icon icon={MessageSquareText} size={14} className="text-muted" />
              <span className="grow">{q.question}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function EntryCard({ entry }: { entry: AskEntry }) {
  return (
    <article aria-label={`Question: ${entry.question}`} className={cn(panel, 'flex flex-col gap-3 px-4 py-3.5')}>
      <p className="text-base font-medium text-ink">{entry.question}</p>
      {entry.status === 'pending' && <Pending phase={entry.phase} />}
      {entry.status === 'error' && <EntryError entry={entry} />}
      {entry.status === 'done' && <Outcome entryKey={entry.key} response={entry.response} />}
    </article>
  );
}

function Pending({ phase }: { phase: 'searching' | 'checking' }) {
  const { cancelAsk } = useActions();
  return (
    <div className="flex items-center gap-2 text-md text-body">
      <Icon icon={LoaderCircle} size={14} spin className="text-muted" />
      <span>{phase === 'searching' ? 'Searching the documents…' : 'Checking every quote…'}</span>
      <span className="grow" />
      <TextLink onClick={cancelAsk}>Cancel</TextLink>
    </div>
  );
}

function EntryError({ entry }: { entry: Extract<AskEntry, { status: 'error' }> }) {
  const { retryAsk } = useActions();
  return (
    <div role="alert" className="flex flex-col gap-1.5 rounded-inner border border-critical px-3.5 py-3">
      <span className="text-md font-medium text-ink">Couldn't get an answer.</span>
      <span className="text-md text-body">{entry.message}</span>
      <div className="pt-1">
        <Button size="sm" onClick={() => retryAsk(entry.key)}>
          Retry
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------- outcomes

function Outcome({ entryKey, response: r }: { entryKey: number; response: AskResponse }) {
  const { setView } = useActions();
  if (r.status === 'answered') return <Answer entryKey={entryKey} response={r} />;
  if (r.status === 'abstained') {
    // Not an error: the documents simply don't say. Message wording comes from the backend.
    return (
      <div className="flex flex-col gap-2.5">
        <p className="flex items-start gap-2 text-base leading-[1.6] text-body">
          <Icon icon={Info} size={15} className="mt-1 text-muted" />
          <span>{r.message}</span>
        </p>
        <Related response={r} />
        <div>
          <TextLink onClick={() => setView('rfi')}>Ask the seller instead</TextLink>
        </div>
      </div>
    );
  }
  return <p className="text-base leading-[1.6] text-body">{r.message}</p>;
}

function Answer({ entryKey, response: r }: { entryKey: number; response: AskResponse }) {
  const route = r.route ? ROUTE[r.route] : null;
  const anyFinding = r.sentences.some((s) => s.finding_id);
  let offset = 0;

  return (
    <div className="flex flex-col gap-3">
      {route && (
        <div className="flex items-center gap-1.5 text-sm text-muted">
          <Icon icon={route.icon} size={13} />
          <span>{route.words}</span>
          <span className="grow" />
          <span className="tabular-nums" title="Time to find and check the answer">
            {(r.latency_ms / 1000).toFixed(1)} s
          </span>
        </div>
      )}
      <p className="text-base leading-[1.9] text-ink">
        {r.sentences.map((s, i) => {
          const first = offset;
          offset += s.citations.length;
          return <Sentence key={i} entryKey={entryKey} sentence={s} firstIndex={first} />;
        })}
      </p>
      <span className="inline-flex items-center gap-1.5 text-sm font-medium text-ok">
        <Icon icon={CircleCheck} size={13} />
        {anyFinding ? 'Every sentence is backed by an exact quote or a finding' : 'Every sentence is backed by an exact quote'}
      </span>
      {r.dropped_sentences > 0 && (
        <p className="flex items-start gap-1.5 text-sm text-muted">
          <Icon icon={Info} size={13} className="mt-0.5" />
          {r.dropped_sentences === 1
            ? "1 sentence was removed because its quote couldn't be verified."
            : `${r.dropped_sentences} sentences were removed because their quotes couldn't be verified.`}
        </p>
      )}
      <Related response={r} />
    </div>
  );
}

/** One answer sentence followed by its citation chips (or its finding chip). */
function Sentence({ entryKey, sentence, firstIndex }: { entryKey: number; sentence: AskSentence; firstIndex: number }) {
  const { state } = useStore();
  const { viewAskSource } = useActions();
  const viewing = state.askViewing;
  return (
    <>
      {sentence.text}{' '}
      {sentence.citations.map((c, j) => {
        const index = firstIndex + j;
        const on = viewing?.entryKey === entryKey && viewing.index === index;
        return (
          <Chip
            key={j}
            icon={FileText}
            active={on}
            aria-pressed={on}
            aria-label={`Open source: ${c.document_title}, page ${c.citation.page}`}
            onClick={() => viewAskSource(entryKey, index)}
          >
            {shortDocTitle(c)}, p. {c.citation.page}
          </Chip>
        );
      })}
      {sentence.finding_id && <FindingChip id={sentence.finding_id} />}{' '}
    </>
  );
}

function FindingChip({ id }: { id: string }) {
  const summary = useSummary();
  const { openEvidence } = useActions();
  const title = summary?.findings.find((f) => f.id === id)?.title;
  return (
    <Chip icon={FileSearch} aria-label={`Open ${findingName(id)}${title ? `: ${title}` : ''}`} onClick={() => openEvidence(id)}>
      {findingName(id)}
    </Chip>
  );
}

function Chip({
  icon,
  active,
  children,
  ...rest
}: { icon: LucideIcon; active?: boolean; children: React.ReactNode } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        'mx-0.5 inline-flex h-6 translate-y-[-1px] items-center gap-1 rounded-pill border px-2 align-middle text-xs font-medium leading-none whitespace-nowrap transition-[background-color,border-color] duration-120',
        active ? 'border-ink bg-surface-strong text-ink' : 'border-hairline bg-surface text-body hover:border-control hover:bg-surface-strong',
      )}
      {...rest}
    >
      <Icon icon={icon} size={12} />
      {children}
    </button>
  );
}

function Related({ response: r }: { response: AskResponse }) {
  const summary = useSummary();
  const { openEvidence, setView } = useActions();
  if (!r.related_finding_id && !r.related_rfi_id) return null;
  const finding = summary?.findings.find((f) => f.id === r.related_finding_id);
  return (
    <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-t border-hairline pt-3 text-md">
      <span className="text-muted">Related</span>
      {r.related_finding_id && (
        <TextLink onClick={() => openEvidence(r.related_finding_id!)} aria-label={finding ? `${findingName(finding.id)}: ${finding.title}` : undefined}>
          {findingName(r.related_finding_id)}
        </TextLink>
      )}
      {r.related_rfi_id && (
        <TextLink onClick={() => setView('rfi')} aria-label={`Seller question ${r.related_rfi_id}`}>
          Seller question {r.related_rfi_id}
        </TextLink>
      )}
    </div>
  );
}

