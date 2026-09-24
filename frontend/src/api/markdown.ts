import type { Rfi } from './types';
import { SEVERITY } from '../lib/status';

/** The RFI list as Markdown. Mirrors GET /api/rfi.md so fixture mode exports the same file. */
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
      '',
      `**Blocks check.** \`${r.check_id}\``,
    ].join('\n'),
  );
  return [`# Requests for information: ${assetName}`, '', ...blocks.flatMap((b) => [b, ''])].join('\n');
}
