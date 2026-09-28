// Places the critical-date labels on the Summary timeline without overlaps.
import type { DateMark } from '../api/types';

export type LabelRow = 'above-far' | 'above-near' | 'below-near';

/** Geometry per row, in px within the 172px-tall plot (axis at 82px). Matches the design. */
export const ROW_GEOMETRY: Record<LabelRow, { top: number; stemTop: number; stemHeight: number }> = {
  'above-far': { top: 0, stemTop: 34, stemHeight: 48 },
  'above-near': { top: 38, stemTop: 72, stemHeight: 10 },
  'below-near': { top: 96, stemTop: 83, stemHeight: 13 },
};

export interface PlacedMark {
  mark: DateMark;
  /** 0..100, position along the axis */
  pct: number;
  row: LabelRow;
  /** Labels in the left part of the axis start at their dot; the rest end at it. */
  anchor: 'start' | 'end';
}

const DAY = 86_400_000;
const time = (iso: string) => Date.parse(`${iso.slice(0, 10)}T00:00:00Z`);

export function positionOf(iso: string, window: { from: string; to: string }): number {
  const from = time(window.from);
  const span = time(window.to) + DAY - from;
  return Math.max(0, Math.min(100, ((time(iso) - from) / span) * 100));
}

/** Year ticks for every 1 January inside the window, plus the window's own start year. */
export function yearTicks(window: { from: string; to: string }): { year: number; pct: number }[] {
  const first = new Date(time(window.from)).getUTCFullYear();
  const last = new Date(time(window.to)).getUTCFullYear();
  const out: { year: number; pct: number }[] = [];
  for (let y = first; y <= last; y++) out.push({ year: y, pct: positionOf(`${y}-01-01`, window) });
  return out;
}

/**
 * Greedy placement: marks are taken left to right and each goes in the first row of its
 * preference order where its label's horizontal extent does not collide with a label
 * already there. `widthPct` estimates a label's width as a
 * percentage of the axis. Clash marks stay near the axis so the band reads clearly.
 */
export function placeMarks(
  marks: DateMark[],
  window: { from: string; to: string },
  widthPct: (m: DateMark) => number,
): PlacedMark[] {
  const sorted = [...marks].sort((a, b) => time(a.date) - time(b.date));
  const taken: Record<LabelRow, [number, number][]> = { 'above-far': [], 'above-near': [], 'below-near': [] };
  const GAP = 1.5; // percent of breathing room between labels in one row
  let clashSeen = 0;

  return sorted.map((mark, i) => {
    const pct = positionOf(mark.date, window);
    const anchor: PlacedMark['anchor'] = pct < 60 ? 'start' : 'end';
    const w = widthPct(mark);
    const extent: [number, number] = anchor === 'start' ? [pct, pct + w] : [pct - w, pct];
    const fits = (row: LabelRow) => taken[row].every(([a, b]) => extent[1] + GAP < a || extent[0] - GAP > b);

    let order: LabelRow[];
    if (mark.tone === 'clash') {
      // First clash date above the axis, second below, so the band between them stays clear.
      order = clashSeen++ === 0 ? ['above-near', 'below-near', 'above-far'] : ['below-near', 'above-near', 'above-far'];
    } else if (mark.tone === 'warning') {
      order = ['above-far', 'above-near', 'below-near'];
    } else if (i === 0) {
      order = ['above-near', 'below-near', 'above-far'];
    } else {
      // Later neutral dates prefer below the axis; the far row is the last resort.
      order = ['below-near', 'above-near', 'above-far'];
    }
    const row = order.find(fits) ?? 'above-far';
    taken[row].push(extent);
    return { mark, pct, row, anchor };
  });
}
