import type { Rfi } from '@design/api/types';
import { SEVERITY } from '../lib/status';

/** The RFI list as Markdown, written for the seller. Mirrors GET /api/rfi.md so fixture mode exports the same file.
 *  Internal references (check names, finding ids) are left out: the seller never sees them. */
export function rfiToMarkdown(rfis: Rfi[], assetName: string): string {
  const blocks = rfis.map((r) =>
    [
      `### ${r.id}: ${r.title} (${SEVERITY[r.severity].word})`,
      '',
      `**Request.** ${r.request}`,
      '',
      `**Why.** ${r.why}`,
      '',
      '**Documents expected.**',
      ...r.documents_expected.map((d) => `- ${d}`),
    ].join('\n'),
  );
  return [`# Requests for information: ${assetName}`, '', ...blocks.flatMap((b) => [b, ''])].join('\n');
}
