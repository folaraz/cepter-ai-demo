import * as React from 'react';
import { cx } from './cx';
import { GradientOrb, type OrbColor } from './GradientOrb';
import './HeroBand.css';

export interface HeroBandProps extends Omit<React.HTMLAttributes<HTMLElement>, 'title'> {
  /** Small label above the headline (usually a <Badge>). */
  eyebrow?: React.ReactNode;
  /** Headline, rendered in display-mega (64px / 300). */
  title: React.ReactNode;
  /** Supporting paragraph. */
  subtitle?: React.ReactNode;
  /** CTA row - typically a primary + an outline <Button>. */
  actions?: React.ReactNode;
  /** Atmospheric orbs behind the headline (first is centred, the rest drift to the sides). Pass [] for none. */
  orbs?: OrbColor[];
  /** Centered (default) or left-aligned layout. */
  align?: 'center' | 'left';
  /** Rare dark-canvas hero. */
  dark?: boolean;
  /** Extra content under the actions (e.g. a product preview). */
  children?: React.ReactNode;
}

const orbPositions = [
  { x: '50%', y: '46%', size: 620 },
  { x: '22%', y: '70%', size: 420 },
  { x: '80%', y: '30%', size: 440 },
];

/** Homepage hero: centered 64px light serif headline over pastel atmospheric orbs, with two CTAs. */
export function HeroBand({ eyebrow, title, subtitle, actions, orbs = ['lavender', 'mint', 'peach'], align = 'center', dark, className, children, ...rest }: HeroBandProps) {
  return (
    <section className={cx('cx-hero', align === 'left' && 'cx-hero--left', dark && 'cx-hero--dark', className)} {...rest}>
      {orbs.slice(0, 3).map((c, i) => (
        <GradientOrb key={i} color={c} x={orbPositions[i].x} y={orbPositions[i].y} size={orbPositions[i].size} />
      ))}
      <div className="cx-hero__inner">
        {eyebrow}
        <h1 className="cx-display-mega">{title}</h1>
        {subtitle && <p className="cx-hero__subtitle">{subtitle}</p>}
        {actions && <div className="cx-hero__actions">{actions}</div>}
        {children}
      </div>
    </section>
  );
}
