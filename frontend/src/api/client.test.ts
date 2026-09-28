import { beforeEach, describe, expect, it } from 'vitest';
import { getDocument, getDocuments, getEvalLatest, getFinding, getRfiMarkdown, getSummary, postReview, resetFixtures, runEval, undoReview } from './client';
import { parseHash, toHash } from '../lib/route';

beforeEach(() => resetFixtures());

describe('fixture client: review loop', () => {
  it('correct returns a golden item id and a stale eval', async () => {
    const res = await postReview('F-03', { action: 'correct', corrected_result: 'fail', reason: 'Different properties.' });
    expect(res.golden_item_id).toBe('corr-002');
    expect(res.eval.state).toBe('stale');
    expect(res.eval.golden_count).toBe(21);
    expect(res.finding.review).toBe('corrected');
    expect(res.finding.result).toBe('fail');
  });

  it('runEval returns to passing and every correction holds', async () => {
    await postReview('F-03', { action: 'correct', corrected_result: 'fail', reason: 'Different properties.' });
    const done = await runEval();
    expect(done.state).toBe('passing');
    expect(done.corrections_held).toBe(2);
    expect(done.corrections_total).toBe(2);
  });

  it('runs the full correct -> stale -> run eval -> passing sequence', async () => {
    expect((await getSummary()).eval.state).toBe('passing');
    const res = await postReview('F-03', { action: 'correct', corrected_result: 'fail', reason: 'Capacity mismatch.' });
    expect(res.eval).toMatchObject({ state: 'stale', corrections_held: 1, corrections_total: 2, golden_count: 21 });

    const summary = await getSummary();
    expect(summary.findings.find((f) => f.id === 'F-03')).toMatchObject({ review: 'corrected', result: 'fail' });
    expect((await getFinding('F-03')).review).toBe('corrected');

    const final = await runEval();
    expect(final).toMatchObject({ state: 'passing', corrections_held: 2, corrections_total: 2 });
    expect((await getEvalLatest()).state).toBe('passing');
  });

  it('rejects reject/correct without a reason', async () => {
    await expect(postReview('F-01', { action: 'reject', reason: '  ' })).rejects.toThrow(/reason/);
  });

  it('accept does not touch the golden set', async () => {
    const res = await postReview('F-02', { action: 'accept' });
    expect(res.golden_item_id).toBeNull();
    expect(res.eval.state).toBe('passing');
    expect(res.finding.review).toBe('lawyer_verified');
  });

  it('undo restores the row and the eval status', async () => {
    const res = await postReview('F-03', { action: 'correct', corrected_result: 'fail', reason: 'x' });
    const row = await undoReview(res.undo_token);
    expect(row).toMatchObject({ review: 'needs_review', result: 'conflict' });
    expect(await getEvalLatest()).toMatchObject({ state: 'passing', golden_count: 20, corrections_total: 1 });
  });
});

describe('fixture client: RFI export', () => {
  it('builds one block per request', async () => {
    const md = await getRfiMarkdown();
    expect(md).toContain('### RFI-01: Cable route rights (Critical)');
    expect(md).toContain('### RFI-03: Confirm export capacity (High)');
    // Written for the seller: no internal check names.
    expect(md).toContain('**Documents expected.**');
    expect(md).not.toMatch(/cable_route_rights|pre_commencement_conditions|Blocks check/);
  });
});

describe('fixture client: documents', () => {
  it('lists the five documents with what each one says', async () => {
    const docs = await getDocuments();
    expect(docs.map((d) => d.id)).toEqual(['lease', 'planning', 'grid', 'ppa', 'site']);
    expect(docs.find((d) => d.id === 'ppa')).toMatchObject({ date: { label: 'Signed', value: '3 Mar 2025' }, pages: 5 });
  });

  it('opens a document whose every note marks a real span of its own paragraph', async () => {
    for (const id of ['lease', 'planning', 'grid', 'ppa', 'site']) {
      const doc = await getDocument(id);
      const text = new Map(doc.pages.flatMap((p) => p.paragraphs.map((q) => [q.id, q.text] as const)));
      expect(doc.notes.length).toBe(doc.document.note_count);
      for (const n of doc.notes) {
        expect(text.has(n.paragraph_id)).toBe(true);
        expect(n.quote_end).toBeLessThanOrEqual(text.get(n.paragraph_id)!.length);
      }
    }
    const ppa = await getDocument('ppa');
    expect(ppa.notes.find((n) => n.label === 'Export capacity')).toMatchObject({ value: '49.9 MW', finding_ids: ['F-03'] });
  });

  it('rejects an unknown document', async () => {
    await expect(getDocument('deed')).rejects.toThrow(/not found/);
  });
});

describe('document routes', () => {
  it('round-trips a deep link to a paragraph and the finding that led there', () => {
    const hash = toHash('documents', 'ppa', { paragraph: 'ppa:p1:¶2', finding: 'F-03' });
    expect(parseHash(hash)).toEqual({ view: 'documents', id: 'ppa', paragraph: 'ppa:p1:¶2', finding: 'F-03' });
    expect(parseHash('#/documents')).toMatchObject({ view: 'documents', id: undefined });
    expect(parseHash('#/evidence/F-03')).toMatchObject({ view: 'evidence', id: 'F-03', paragraph: undefined });
  });
});
