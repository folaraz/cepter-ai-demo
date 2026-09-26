import { beforeEach, describe, expect, it } from 'vitest';
import { getEvalLatest, getFinding, getRfiMarkdown, getSummary, postReview, resetFixtures, runEval, undoReview } from './client';

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
