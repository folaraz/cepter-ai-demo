import * as React from 'react';
import { cx } from './cx';
import './Badge.css';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** default = warm grey plate; outline = hairline ring; ink = near-black; on-dark = for dark bands. */
  tone?: 'default' | 'outline' | 'ink' | 'on-dark';
  /** `pill` = uppercase caption label (default); `tag` = small sentence-case inline tag with 4px radius. */
  shape?: 'pill' | 'tag';
  /** Leading status dot. */
  dot?: boolean | 'success';
}

/** Uppercase pill label for section eyebrows, plan names and statuses. */
export function Badge({ tone = 'default', shape = 'pill', dot, className, children, ...rest }: BadgeProps) {
  return (
    <span className={cx('cx-badge', `cx-badge--${tone}`, shape === 'tag' && 'cx-badge--tag', className)} {...rest}>
      {dot && <span className={cx('cx-badge__dot', dot === 'success' && 'cx-badge__dot--success')} aria-hidden />}
      {children}
    </span>
  );
}
