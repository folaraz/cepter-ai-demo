import type { View } from '../state/store';

const VIEW_PATH: Record<View, string> = { summary: 'summary', evidence: 'evidence', documents: 'documents', rfi: 'requests', ask: 'ask' };

export interface Route {
  view: View;
  /** A finding for summary and evidence; a document for documents. */
  id?: string;
  /** Documents only: the paragraph to open at, and the finding that led there. */
  paragraph?: string;
  finding?: string;
}

/** "#/evidence/F-03" -> { view: "evidence", id: "F-03" }; "#/documents/ppa/ppa%3Ap1%3A%C2%B62/F-03" -> the reader at that paragraph. */
export function parseHash(hash: string): Route | null {
  const [path, id, paragraph, finding] = hash.replace(/^#\/?/, '').split('/').map(safeDecode);
  const view = (Object.keys(VIEW_PATH) as View[]).find((v) => VIEW_PATH[v] === path);
  if (!view) return null;
  return { view, id: id || undefined, paragraph: view === 'documents' ? paragraph || undefined : undefined, finding: view === 'documents' ? finding || undefined : undefined };
}

export function toHash(view: View, id: string | null, doc?: { paragraph?: string; finding?: string } | null): string {
  if (view === 'documents') {
    const parts = [id, doc?.paragraph, doc?.paragraph ? doc.finding : undefined].filter((x): x is string => !!x);
    return `#/documents${parts.map((p) => `/${encodeURIComponent(p)}`).join('')}`;
  }
  return `#/${VIEW_PATH[view]}${(view === 'summary' || view === 'evidence') && id ? `/${id}` : ''}`;
}

function safeDecode(s: string) {
  try {
    return decodeURIComponent(s);
  } catch {
    return s;
  }
}
