import * as React from 'react';
import { cx } from './cx';
import { GradientOrb, type OrbColor } from './GradientOrb';
import './CtaBand.css';

export interface CtaBandProps extends Omit<React.HTMLAttributes<HTMLElement>, 'title'> {
  /** Centered display-lg headline. */
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  /** Usually a single primary <Button>. */
  actions?: React.ReactNode;
  /** Optional soft orb behind the headline. */
  orb?: OrbColor;
  /** Dark surface variant. */
  dark?: boolean;
}

/** Pre-footer call-to-action band: centered serif headline + single ink pill, 96px padding. */
export function CtaBand({ title, subtitle, actions, orb, dark, className, ...rest }: CtaBandProps) {
  return (
    <section className={cx('cx-cta-band', dark && 'cx-cta-band--dark', className)} {...rest}>
      {orb && <GradientOrb color={orb} size={520} />}
      <div className="cx-cta-band__inner">
        <h2 className="cx-display-lg">{title}</h2>
        {subtitle && <p className="cx-cta-band__subtitle">{subtitle}</p>}
        {actions && <div className="cx-cta-band__actions">{actions}</div>}
      </div>
    </section>
  );
}
