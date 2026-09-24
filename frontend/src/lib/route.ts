import type { View } from '../state/store';

const VIEW_PATH: Record<View, string> = { summary: 'summary', evidence: 'evidence', rfi: 'requests' };

/** "#/evidence/F-03" -> { view: "evidence", id: "F-03" } */
export function parseHash(hash: string): { view: View; id?: string } | null {
  const [path, id] = hash.replace(/^#\/?/, '').split('/');
  const view = (Object.keys(VIEW_PATH) as View[]).find((v) => VIEW_PATH[v] === path);
  return view ? { view, id: id || undefined } : null;
}

export function toHash(view: View, id: string | null): string {
  return `#/${VIEW_PATH[view]}${view !== 'rfi' && id ? `/${id}` : ''}`;
}
