import { useMemo } from 'react';
import type { DateMark, Summary } from '../api/types';
import { formatDate } from '../lib/format';
import { placeMarks, ROW_GEOMETRY, yearTicks } from '../lib/timeline';
import { useActions } from '../state/store';
import { CircleX } from 'lucide-react';
import { hit, Icon, panel, SectionHeading, Sk } from '../components/ui';
import { cn } from '../lib/cn';

const TONE_COLOR: Record<DateMark['tone'], string> = {
  neutral: 'var(--ink)',
  clash: 'var(--critical)',
  warning: 'var(--conflict)',
};

// Rough label width as a share of a ~1030px axis: the longer of the two lines.
const labelWidthPct = (m: DateMark) => (Math.max(m.label.length * 6, formatDate(m.date).length * 7.2) / 1030) * 100;

// Below 900px the plot keeps its desktop width and the card scrolls sideways.
const card = cn(panel, 'relative px-6 pt-4 pb-4 max-md:overflow-x-auto');
const plot = 'relative mt-3 h-[172px] max-md:min-w-[820px]';
const beyond = cn(
  hit,
  'mt-1 flex min-h-9 w-full items-center gap-3 rounded-[6px] border-none bg-transparent px-2.5 py-2 text-left text-md max-md:min-w-[820px]',
);

function Head({ scale }: { scale?: string }) {
  return (
    <SectionHeading id="dates-h" title="Critical dates" description={scale} />
  );
}

const Axis = () => <div aria-hidden="true" className="absolute inset-x-0 top-[82px] h-px bg-control" />;

export function DatesCard({ summary }: { summary: Summary | null }) {
  const { openEvidence } = useActions();
  const placed = useMemo(() => (summary ? placeMarks(summary.dates, summary.date_window, labelWidthPct) : []), [summary]);

  if (!summary) {
    return (
      <section aria-labelledby="dates-h" aria-busy="true" className={card}>
        <Head />
        <div className={plot} aria-hidden="true">
          <Axis />
        </div>
        <div className={beyond} aria-hidden="true">
          <Sk className="w-[60%]" />
        </div>
      </section>
    );
  }

  const w = summary.date_window;
  const toYear = w.to.slice(0, 4);
  const byKey = Object.fromEntries(placed.map((p) => [p.mark.key, p]));
  const clashFrom = byKey[summary.clash.from_key];
  const clashTo = byKey[summary.clash.to_key];
  const lh = summary.long_horizon;

  return (
    <section aria-labelledby="dates-h" className={card}>
      <Head scale={`${w.from.slice(0, 4)} to ${toYear}, drawn to scale. Select a date to see its source.`} />
      <div className={plot}>
        <Axis />
        {clashFrom && clashTo && (
          // Pointer shortcut only; the clash label below is the accessible control.
          <div
            aria-hidden="true"
            className="absolute top-[79px] h-[7px] cursor-pointer rounded-[2px] bg-critical opacity-35"
            style={{ left: `${clashFrom.pct}%`, width: `${clashTo.pct - clashFrom.pct}%` }}
            onClick={() => openEvidence(summary.clash.finding_id)}
          />
        )}
        {placed.map(({ mark, pct, row, anchor }) => {
          const g = ROW_GEOMETRY[row];
          const color = TONE_COLOR[mark.tone];
          return (
            <div key={mark.key}>
              <div aria-hidden="true" className="absolute w-px bg-control" style={{ left: `${pct}%`, top: g.stemTop, height: g.stemHeight }} />
              <div
                aria-hidden="true"
                className="absolute top-[78px] size-[9px] rounded-[5px] border-2 border-surface"
                style={{ left: `calc(${pct}% - 4px)`, background: color }}
              />
              <button
                type="button"
                className={cn(
                  'group absolute flex flex-col gap-px whitespace-nowrap rounded-[4px] border-none bg-transparent p-0',
                  anchor === 'start' ? 'items-start text-left' : 'items-end text-right',
                )}
                style={{ top: g.top, ...(anchor === 'start' ? { left: `${pct}%` } : { right: `${100 - pct}%` }) }}
                onClick={() => openEvidence(mark.finding_id)}
              >
                <span className="text-md font-semibold" style={{ color }}>
                  {formatDate(mark.date)}
                </span>
                <span className="text-xs text-muted group-hover:text-ink">{mark.label}</span>
              </button>
            </div>
          );
        })}
        {clashTo && (
          <button
            type="button"
            className="absolute top-[130px] inline-flex items-center gap-1.5 whitespace-nowrap border-none bg-transparent p-0 text-sm font-medium text-critical underline-offset-3 hover:underline"
            style={{ right: `${100 - clashTo.pct}%` }}
            onClick={() => openEvidence(summary.clash.finding_id)}
          >
            <Icon icon={CircleX} size={13} />
            {summary.clash.label}
          </button>
        )}
        {yearTicks(w).map((y) => (
          <span key={y.year} aria-hidden="true" className="absolute top-[156px] w-7 text-center text-xs text-muted tabular-nums" style={{ left: `calc(${y.pct}% - 14px)` }}>
            {y.year}
          </span>
        ))}
      </div>
      <button type="button" className={beyond} onClick={() => openEvidence(lh.finding_id)}>
        <span className="shrink-0 font-semibold text-ink">After {toYear}</span>
        <span>{lh.text}</span>
        <span className="grow" />
        <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-medium text-critical">
          <Icon icon={CircleX} size={13} />
          {lh.flag}
        </span>
      </button>
    </section>
  );
}
