import { useEffect, useState } from 'react';
import { useActions, useStore, useSummary } from '../state/store';
import { ChevronRight, Keyboard, Moon, Sun } from 'lucide-react';
import { BrandMark, Icon, IconButton } from './ui';
import { findingName } from '../lib/format';

type Theme = 'light' | 'dark';

const systemTheme = (): Theme => (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

function useTheme(): [Theme, () => void] {
  const [theme, setTheme] = useState<Theme>(() => (document.documentElement.dataset.theme as Theme) || systemTheme());
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => {
    // Follow the system until the user picks a theme.
    const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
    const onChange = () => {
      let saved: string | null = null;
      try { saved = localStorage.getItem('drl-theme'); } catch { /* storage unavailable */ }
      if (!saved) setTheme(systemTheme());
    };
    mq?.addEventListener('change', onChange);
    return () => mq?.removeEventListener('change', onChange);
  }, []);
  const toggle = () =>
    setTheme((t) => {
      const next = t === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem('drl-theme', next); } catch { /* storage unavailable */ }
      return next;
    });
  return [theme, toggle];
}

const CRUMB = { summary: 'Summary', evidence: 'Evidence', documents: 'Documents', rfi: 'Seller questions', ask: 'Ask' } as const;

export function TopBar() {
  const { state } = useStore();
  const summary = useSummary();
  const { setHelp } = useActions();
  const [theme, toggleTheme] = useTheme();
  const docTitle = state.view === 'documents' && state.docId ? summary?.documents.find((d) => d.id === state.docId)?.title : undefined;
  const crumb = state.view === 'evidence' && state.selectedId ? `Evidence · ${findingName(state.selectedId)}` : (docTitle ?? CRUMB[state.view]);

  return (
    <header className="flex h-(--topbar-h) shrink-0 items-center gap-4 border-b border-hairline bg-surface px-4">
      <div className="flex w-[216px] shrink-0 items-center gap-2.5 max-md:w-auto">
        <BrandMark />
        <span className="text-lg font-semibold tracking-tight">DataRoom Lens</span>
      </div>
      <nav aria-label="Breadcrumb" className="max-md:hidden">
        <ol className="flex items-center gap-1.5 whitespace-nowrap text-md text-muted">
          <li>{summary?.asset.name ?? 'Brackenfield Solar & Storage'}</li>
          <li aria-hidden="true">
            <Icon icon={ChevronRight} size={14} />
          </li>
          <li aria-current="page" className="font-medium text-ink">
            {crumb}
          </li>
        </ol>
      </nav>
      <div className="grow" />
      {(summary?.asset.synthetic ?? true) && (
        <span
          title="This is a sample deal with made-up documents, for demonstration."
          className="inline-flex h-6 items-center rounded-pill bg-surface-strong px-2.5 text-xs font-medium text-body max-lg:hidden"
        >
          Demo data
        </span>
      )}
      <div className="flex items-center gap-1.5">
        <IconButton
          icon={theme === 'dark' ? Sun : Moon}
          onClick={toggleTheme}
          aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
        />
        <IconButton icon={Keyboard} onClick={() => setHelp(true)} aria-label="Keyboard shortcuts" title="Keyboard shortcuts (?)" />
      </div>
    </header>
  );
}
