import * as React from 'react';
import { cx } from './cx';
import { Button } from './Button';
import { Badge } from './Badge';
import './PricingTierCard.css';

export interface PricingTierCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Plan name, e.g. "Creator". */
  name: React.ReactNode;
  /** Price label, e.g. "$22" or "Custom". */
  price: React.ReactNode;
  /** Period suffix, e.g. "/month". */
  period?: React.ReactNode;
  description?: React.ReactNode;
  /** Bullet list of included features. */
  features?: React.ReactNode[];
  /** CTA label; renders a block pill button. */
  ctaLabel?: string;
  onCtaClick?: () => void;
  /** Custom CTA node (replaces ctaLabel). */
  cta?: React.ReactNode;
  /** Dark inverted tier for the recommended plan. */
  featured?: boolean;
  /** Small pill in the name row, e.g. "Most popular". */
  badge?: React.ReactNode;
}

const Check = () => (<svg className="cx-pricing__check" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden><path d="M3 8.5l3.2 3L13 4.5" /></svg>);

/** Pricing plan card. `featured` inverts to the dark surface with a white pill CTA. */
export function PricingTierCard({ name, price, period, description, features = [], ctaLabel, onCtaClick, cta, featured, badge, className, ...rest }: PricingTierCardProps) {
  return (
    <div className={cx('cx-pricing', featured && 'cx-pricing--featured', className)} {...rest}>
      <div className="cx-pricing__head">
        <div className="cx-pricing__name-row">
          <h3 className="cx-pricing__name">{name}</h3>
          {badge && <Badge tone={featured ? 'on-dark' : 'default'}>{badge}</Badge>}
        </div>
        {description && <p className="cx-pricing__description">{description}</p>}
      </div>
      <div className="cx-pricing__price">
        <span className="cx-pricing__amount">{price}</span>
        {period && <span className="cx-pricing__period">{period}</span>}
      </div>
      {features.length > 0 && (
        <ul className="cx-pricing__features">
          {features.map((f, i) => (<li key={i} className="cx-pricing__feature"><Check />{f}</li>))}
        </ul>
      )}
      <div className="cx-pricing__cta">
        {cta ?? (ctaLabel && <Button block variant={featured ? 'primary' : 'outline'} onDark={featured} onClick={onCtaClick}>{ctaLabel}</Button>)}
      </div>
    </div>
  );
}
