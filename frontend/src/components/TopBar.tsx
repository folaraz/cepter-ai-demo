import { useEffect, useState } from 'react';
import { useActions, useStore, useSummary } from '../state/store';
import { Button, Glyph, Kbd } from './ui';

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

const CRUMB = { summary: 'Summary', evidence: 'Evidence', rfi: 'Requests' } as const;

export function TopBar() {
  const { state } = useStore();
  const summary = useSummary();
  const { setHelp } = useActions();
  const [theme, toggleTheme] = useTheme();
  const crumb = state.view === 'evidence' && state.selectedId ? `Evidence · ${state.selectedId}` : CRUMB[state.view];

  return (
    <header className="flex h-(--topbar-h) shrink-0 items-center gap-4 border-b border-hairline bg-surface px-4">
      <div className="flex w-[216px] shrink-0 items-center gap-2 max-md:w-auto">
        <span aria-hidden="true" className="inline-flex size-5 items-center justify-center rounded-pill bg-primary">
          <span className="size-1.5 rounded-[3px] bg-on-primary" />
        </span>
        <span className="text-lg font-medium tracking-tight">DataRoom Lens</span>
      </div>
      <nav aria-label="Breadcrumb" className="max-md:hidden">
        <ol className="flex items-center gap-2 whitespace-nowrap text-md text-muted">
          <li>{summary?.asset.name ?? 'Brackenfield Solar & Storage'}</li>
          <li aria-current="page" className="font-medium text-ink before:mr-2 before:font-normal before:text-muted before:content-['/']">
            {crumb}
          </li>
        </ol>
      </nav>
      <div className="grow" />
      {(summary?.asset.synthetic ?? true) && (
        <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-sm font-medium text-muted max-lg:hidden">
          <Glyph>◇</Glyph>Synthetic data room · offline replay
        </span>
      )}
      <Button size="sm" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}>
        <Glyph>{theme === 'dark' ? '○' : '●'}</Glyph>
        <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
      </Button>
      <Button size="sm" onClick={() => setHelp(true)} aria-label="Keyboard shortcuts">
        <Kbd>?</Kbd>
        <span>Shortcuts</span>
      </Button>
    </header>
  );
}
