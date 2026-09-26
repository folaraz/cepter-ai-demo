import { Button } from './ui';

/** A scoped, retryable error in the interface's voice. Never a blank screen. */
export function ErrorNote({ title, detail, onRetry }: { title: string; detail?: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col gap-1.5 rounded-inner border border-critical bg-surface px-4 py-3.5">
      <span className="text-base font-medium">{title}</span>
      <span className="text-md text-body">{detail ?? 'Check your connection, then try again.'}</span>
      <div className="pt-0.5">
        <Button tone="ink" onClick={onRetry}>
          Retry
        </Button>
      </div>
    </div>
  );
}
