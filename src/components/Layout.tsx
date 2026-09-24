import * as React from 'react';
import { cx } from './cx';
import './Layout.css';

export interface PageProps extends React.HTMLAttributes<HTMLDivElement> {}

/** Page root: sets the canvas background, Inter body type and box-sizing. Wrap every screen in it. */
export function Page({ className, ...rest }: PageProps) {
  return <div className={cx('cx-page', 'cx-root', className)} {...rest} />;
}

export interface ContainerProps extends React.HTMLAttributes<HTMLDivElement> {}

/** Centered content column, max 1200px with 24px side gutters. */
export function Container({ className, ...rest }: ContainerProps) {
  return <div className={cx('cx-container', className)} {...rest} />;
}

export interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  /** Band background. `dark` inverts headings to white. */
  tone?: 'canvas' | 'soft' | 'card' | 'dark';
  /** 48px vertical padding instead of the 96px section rhythm. */
  compact?: boolean;
  /** Wrap children in a Container. Default true. */
  contained?: boolean;
}

/** Full-width band with the 96px editorial section rhythm. */
export function Section({ tone = 'canvas', compact, contained = true, className, children, ...rest }: SectionProps) {
  return (
    <section className={cx('cx-section', `cx-section--${tone}`, compact && 'cx-section--compact', className)} {...rest}>
      {contained ? <div className="cx-container">{children}</div> : children}
    </section>
  );
}

export interface GridProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Columns at desktop; collapses 3/4 -> 2 -> 1 responsively. */
  columns?: 2 | 3 | 4;
  /** Gap token. Default `lg` (24px). */
  gap?: 'base' | 'md' | 'lg' | 'xl';
}

/** Responsive card grid (2-up hero splits, 3-up benefit grids). */
export function Grid({ columns = 3, gap = 'lg', className, style, ...rest }: GridProps) {
  return <div className={cx('cx-grid', `cx-grid--${columns}`, className)} style={{ gap: `var(--cx-space-${gap})`, ...style }} {...rest} />;
}
