// Fixed three-letter months: Intl's en-GB output ("Sept") varies by runtime.
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const pad = (n: number) => String(n).padStart(2, '0');

/** "2029-03-31" -> "31 Mar 2029" */
export const formatDate = (iso: string) => {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

/** "2026-09-21T14:02:00Z" -> "21 Sep 14:02" (run times are shown in UTC, as the backend records them) */
export const formatRunTime = (iso: string) => {
  const d = new Date(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
};

export const percent = (v: number) => `${Math.round(v * 100)}%`;

export const gbp = (v: number) => `£${v.toFixed(2)}`;

export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** "3 verified quotes · 1 gap" */
export const evidenceLine = (quotes: number, gaps: number) =>
  plural(quotes, 'verified quote') + (gaps ? ` · ${plural(gaps, 'gap')}` : '');

export const rowNumber = (i: number) => String(i + 1).padStart(2, '0');
