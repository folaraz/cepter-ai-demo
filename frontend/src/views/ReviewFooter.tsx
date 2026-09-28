import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import type { CheckResult, Finding } from '@design/api/types';
import { RESULT, RESULT_ORDER } from '../lib/status';
import { useActions, useStore } from '../state/store';
import { Check, CircleAlert } from 'lucide-react';
import { Button, Icon } from '../components/ui';

export function ReviewFooter({ finding }: { finding: Finding }) {
  const { state } = useStore();
  const { review, setMode } = useActions();
  const mode = state.reviewMode;
  const [reason, setReason] = useState('');
  const [corrected, setCorrected] = useState<CheckResult>(() => RESULT_ORDER.find((r) => r !== finding.result) ?? 'fail');
  const [invalid, setInvalid] = useState(false);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const errId = useId();

  // Each time a form opens it starts clean.
  useEffect(() => {
    if (mode === 'idle') {
      setReason('');
      setInvalid(false);
    }
  }, [mode]);

  const cancel = () => {
    const back = mode === 'reject' ? 'review-reject' : 'review-correct';
    setMode('idle');
    requestAnimationFrame(() => document.querySelector<HTMLElement>(`[data-focus="${back}"]`)?.focus());
  };

  const save = async () => {
    if (!reason.trim()) {
      setInvalid(true);
      reasonRef.current?.focus();
      return;
    }
    await review(mode === 'correct' ? 'correct' : 'reject', {
      reason: reason.trim(),
      ...(mode === 'correct' ? { corrected_result: corrected } : {}),
    });
  };

  const onFormKey = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      cancel();
    } else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void save();
    }
  };

  return (
    <div className="flex shrink-0 flex-col gap-2.5 border-t border-hairline bg-surface px-7 pt-4 pb-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="text-sm font-semibold text-ink">Your review</h2>
        <span className="text-sm text-muted">Corrections are remembered and re-checked on every run</span>
      </div>

      {mode === 'idle' ? (
        <div className="flex gap-2">
          <Button tone="ink" grow data-focus="review-accept" title="Accept (A)" aria-disabled={state.saving} onClick={() => review('accept')}>
            <Icon icon={Check} size={15} />
            Accept
          </Button>
          <Button grow data-focus="review-reject" title="Reject (R)" onClick={() => setMode('reject')}>
            Reject
          </Button>
          <Button grow data-focus="review-correct" title="Correct (C)" onClick={() => setMode('correct')}>
            Correct
          </Button>
        </div>
      ) : (
        <form
          className="flex flex-col gap-2.5"
          onKeyDown={onFormKey}
          onSubmit={(e) => {
            e.preventDefault();
            void save();
          }}
          noValidate
        >
          {mode === 'correct' && (
            <label className="grid grid-cols-[110px_1fr] items-center gap-2.5 text-md text-body">
              <span>Right result</span>
              <select
                className="h-(--input-h) rounded-input border border-control bg-surface px-3 text-base text-ink"
                data-focus="review-select"
                value={corrected}
                onChange={(e) => setCorrected(e.target.value as CheckResult)}
              >
                {RESULT_ORDER.map((r) => (
                  <option key={r} value={r}>
                    {RESULT[r].word}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label htmlFor="review-reason" className="text-md text-body">
            {mode === 'correct' ? 'Why? Your team will see this.' : 'Why is this finding wrong? Your team will see this.'}
          </label>
          <textarea
            id="review-reason"
            ref={reasonRef}
            className="w-full resize-none rounded-input border border-control bg-surface px-3.5 py-3 text-base leading-normal text-ink aria-invalid:border-critical"
            data-focus="review-reason"
            rows={3}
            required
            value={reason}
            aria-invalid={invalid}
            aria-describedby={invalid ? errId : undefined}
            placeholder={
              mode === 'correct'
                ? 'e.g. The planning limit and the grid limit are different things, so this is a real shortfall, not a disagreement.'
                : 'e.g. The lease plan annex already grants these rights.'
            }
            onChange={(e) => {
              setReason(e.target.value);
              if (invalid && e.target.value.trim()) setInvalid(false);
            }}
          />
          {invalid && (
            <span id={errId} data-part="reason-error" className="inline-flex items-center gap-1.5 text-sm font-medium text-critical">
              <Icon icon={CircleAlert} size={13} />Add a short reason so your team knows why.
            </span>
          )}
          <div className="flex gap-2">
            <Button onClick={cancel}>Cancel</Button>
            <Button type="submit" tone="ink" grow aria-disabled={state.saving}>
              {state.saving ? 'Saving…' : mode === 'correct' ? 'Save correction' : 'Dismiss finding'}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
