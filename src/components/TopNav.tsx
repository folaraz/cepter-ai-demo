import * as React from 'react';
import { cx } from './cx';
import './TopNav.css';

export interface NavLinkItem {
  label: string;
  href?: string;
  active?: boolean;
}

export interface TopNavProps extends React.HTMLAttributes<HTMLElement> {
  /** Wordmark text or custom node. Default "cepter ai demo". */
  brand?: React.ReactNode;
  /** Show the small pastel orb mark before the wordmark. Default true. */
  showMark?: boolean;
  /** Primary horizontal menu. */
  links?: NavLinkItem[];
  /** Right-side actions - typically text "Sign in" + primary "Try free" Buttons (size="sm"). */
  actions?: React.ReactNode;
  /** canvas (default), transparent (over a hero) or dark. */
  tone?: 'canvas' | 'transparent' | 'dark';
  /** Bottom hairline. */
  bordered?: boolean;
  /** Mobile hamburger press (menu shows below 960px). */
  onMenuClick?: () => void;
}

/** 64px top navigation: wordmark left, pill-hover menu, actions right; collapses to a hamburger under 960px. */
export function TopNav({ brand = 'cepter ai demo', showMark = true, links = [], actions, tone = 'canvas', bordered, onMenuClick, className, ...rest }: TopNavProps) {
  return (
    <nav className={cx('cx-nav', tone !== 'canvas' && `cx-nav--${tone}`, bordered && 'cx-nav--bordered', className)} {...rest}>
      <div className="cx-nav__inner">
        <a className="cx-nav__brand" href="#">
          {showMark && <span className="cx-nav__mark" aria-hidden />}
          {brand}
        </a>
        <ul className="cx-nav__links">
          {links.map((l) => (
            <li key={l.label}>
              <a className={cx('cx-nav__link', l.active && 'cx-nav__link--active')} href={l.href ?? '#'} aria-current={l.active ? 'page' : undefined}>{l.label}</a>
            </li>
          ))}
        </ul>
        {actions && <div className="cx-nav__actions">{actions}</div>}
        <button type="button" className="cx-nav__menu" aria-label="Open menu" onClick={onMenuClick}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"><path d="M4 8h16M4 16h16" /></svg>
        </button>
      </div>
    </nav>
  );
}
