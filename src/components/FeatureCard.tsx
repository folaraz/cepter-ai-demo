import * as React from 'react';
import { cx } from './cx';
import './Cards.css';

export interface FeatureCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Small glyph shown on a 40px warm-grey plate. */
  icon?: React.ReactNode;
  /** Optional label above the title (e.g. <Badge>). */
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Bottom-aligned slot (e.g. a text <Button>). */
  footer?: React.ReactNode;
  /** Adds the soft-drop hover shadow and pointer cursor. */
  interactive?: boolean;
}

/** White 16px-radius card with hairline border, for 2-up / 3-up benefit grids. */
export function FeatureCard({ icon, eyebrow, title, description, footer, interactive, className, children, ...rest }: FeatureCardProps) {
  return (
    <div className={cx('cx-feature-card', interactive && 'cx-feature-card--interactive', className)} {...rest}>
      {icon && <span className="cx-feature-card__icon" aria-hidden>{icon}</span>}
      {eyebrow}
      <h3 className="cx-title-md">{title}</h3>
      {description && <p className="cx-feature-card__description">{description}</p>}
      {children}
      {footer && <div className="cx-feature-card__footer">{footer}</div>}
    </div>
  );
}
