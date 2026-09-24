import * as React from 'react';
import { cx } from './cx';
import { GradientOrb, type OrbColor } from './GradientOrb';
import './GradientOrbCard.css';

export interface GradientOrbCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Which pastel orb blooms behind the copy. */
  tone?: OrbColor;
  /** Optional label above the title (e.g. <Badge>). */
  eyebrow?: React.ReactNode;
  /** Centered display copy (display-md serif). */
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Actions or extra content below the copy. */
  footer?: React.ReactNode;
  /** Minimum height in px (default 320). */
  minHeight?: number;
}

/** Large extra-soft (24px radius) card with a single pastel orb behind centered serif copy. */
export function GradientOrbCard({ tone = 'lavender', eyebrow, title, description, footer, minHeight, className, style, children, ...rest }: GradientOrbCardProps) {
  return (
    <div className={cx('cx-orb-card', className)} style={{ minHeight, ...style }} {...rest}>
      <GradientOrb color={tone} size={340} />
      <div className="cx-orb-card__content">
        {eyebrow}
        <h3 className="cx-display-md">{title}</h3>
        {description && <p className="cx-orb-card__description">{description}</p>}
        {children}
      </div>
      {footer && <div className="cx-orb-card__footer">{footer}</div>}
    </div>
  );
}
