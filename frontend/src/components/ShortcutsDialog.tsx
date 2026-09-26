import { useEffect, useRef } from 'react';
import { useActions, useStore } from '../state/store';
import { X } from 'lucide-react';
import { Button, Icon, Kbd, panel } from './ui';
import { cn } from '../lib/cn';

const SHORTCUTS: { what: string; keys: string[] }[] = [
  { what: 'Next / previous finding', keys: ['J', 'K'] },
  { what: 'Open evidence', keys: ['↵'] },
  { what: 'Accept a finding', keys: ['A'] },
  { what: 'Correct a finding', keys: ['C'] },
  { what: 'Reject a finding', keys: ['R'] },
  { what: 'Resize the two panels (divider selected)', keys: ['←', '→'] },
  { what: 'Ask a question', keys: ['/'] },
  { what: 'Show these shortcuts', keys: ['?'] },
  { what: 'Close dialog or form', keys: ['Esc'] },
];

/** Native modal dialog: focus is contained, Esc closes, focus returns to whatever opened it. */
export function ShortcutsDialog() {
  const { state } = useStore();
  const { setHelp } = useActions();
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (state.helpOpen && !dialog.open) {
      opener.current = document.activeElement as HTMLElement | null;
      dialog.showModal();
    } else if (!state.helpOpen && dialog.open) {
      dialog.close();
    }
  }, [state.helpOpen]);

  const onClose = () => {
    setHelp(false);
    const back = opener.current;
    opener.current = null;
    // Chrome fires "close" a moment after the dialog shuts. If focus has already moved on
    // (e.g. "/" jumped to the Ask input), leave it there instead of pulling it back.
    const active = document.activeElement;
    const focusIsFree = !active || active === document.body || ref.current?.contains(active);
    // The opener may be body when ? was pressed with nothing focused.
    if (focusIsFree && back && back !== document.body && back.isConnected) back.focus();
  };

  return (
    <dialog
      ref={ref}
      className={cn(panel, 'm-auto w-[480px] max-w-[calc(100vw-32px)] px-8 py-7 text-ink shadow-lift open:flex open:flex-col open:gap-4')}
      aria-labelledby="help-h"
      onClose={onClose}
      onClick={(e) => {
        if (e.target === ref.current) setHelp(false); // click on the backdrop
      }}
    >
      <div className="flex items-center justify-between">
        <h2 id="help-h" className="font-display text-dialog font-light tracking-display">
          Keyboard shortcuts
        </h2>
        <Button size="icon" aria-label="Close" onClick={() => setHelp(false)} autoFocus>
          <Icon icon={X} size={16} />
        </Button>
      </div>
      <dl className="flex flex-col gap-2.5 text-md">
        {SHORTCUTS.map((s) => (
          <div key={s.what} className="flex items-center justify-between gap-6">
            <dt className="text-body">{s.what}</dt>
            <dd className="flex gap-1">
              {s.keys.map((k) => (
                <Kbd key={k} large>{k}</Kbd>
              ))}
            </dd>
          </div>
        ))}
      </dl>
      <p className="text-sm text-muted">Single-key shortcuts never fire while you are typing in a field.</p>
    </dialog>
  );
}
