// Fixed three-letter months: Intl's en-GB output ("Sept") varies by runtime.
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const pad = (n: number) => String(n).padStart(2, '0');

/** "2029-03-31" -> "31 Mar 2029" */
export const formatDate = (iso: string) => {
  const d = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
};

/** "2026-09-21T14:02:00Z" -> "21 Sep 2026 at 14:02" (run times are shown in UTC, as the backend records them) */
export const formatRunTime = (iso: string) => {
  const d = new Date(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()} at ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
};

export const percent = (v: number) => `${Math.round(v * 100)}%`;

export const gbp = (v: number) => `£${v.toFixed(2)}`;

export const plural = (n: number, one: string, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

/** "3 quotes · 1 missing document" */
export const evidenceLine = (quotes: number, gaps: number) =>
  plural(quotes, 'quote') + (gaps ? ` · ${plural(gaps, 'missing document')}` : '');

// Short names for citation chips; the full title is in the chip's accessible label.
const SHORT_DOC: Record<string, string> = {
  lease: 'Lease',
  planning: 'Planning decision',
  grid: 'Grid offer',
  ppa: 'PPA',
  site: 'Site plan',
};

/** "Grid connection offer" -> "Grid offer" (falls back to the full title). */
export const shortDocTitle = (q: { citation: { document_id: string }; document_title: string }) =>
  SHORT_DOC[q.citation.document_id] ?? q.document_title;

/** "F-03" -> "Finding 3" */
export const findingName = (id: string) => `Finding ${Number(id.replace(/\D/g, '')) || id}`;

export const rowNumber = (i: number) => String(i + 1).padStart(2, '0');
