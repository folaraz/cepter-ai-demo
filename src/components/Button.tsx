import * as React from 'react';
import { cx } from './cx';
import './Button.css';

export interface ButtonProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'type'> {
  /** `primary` = ink pill (the only CTA colour); `outline` = transparent pill with hairline border; `text` = inline ink link. */
  variant?: 'primary' | 'outline' | 'text';
  /** md = 40px (default), sm = 32px, lg = 48px. */
  size?: 'sm' | 'md' | 'lg';
  /** Invert for dark surfaces (Section tone="dark", featured pricing). */
  onDark?: boolean;
  /** Stretch to container width. */
  block?: boolean;
  /** Render as a link. */
  href?: string;
  /** Icon before the label. */
  leadingIcon?: React.ReactNode;
  /** Icon after the label. */
  trailingIcon?: React.ReactNode;
  type?: 'button' | 'submit' | 'reset';
}

/** Pill button. Use one `primary` per view; pair with `outline` for the secondary action. */
export function Button({ variant = 'primary', size = 'md', onDark, block, href, leadingIcon, trailingIcon, className, children, type = 'button', ...rest }: ButtonProps) {
  const classes = cx('cx-button', `cx-button--${variant}`, `cx-button--${size}`, onDark && 'cx-button--on-dark', block && 'cx-button--block', className);
  const content = (
    <>
      {leadingIcon && <span className="cx-button__icon" aria-hidden>{leadingIcon}</span>}
      {children}
      {trailingIcon && <span className="cx-button__icon" aria-hidden>{trailingIcon}</span>}
    </>
  );
  if (href) {
    return <a href={href} className={classes} {...(rest as React.AnchorHTMLAttributes<HTMLAnchorElement>)}>{content}</a>;
  }
  return <button type={type} className={classes} {...rest}>{content}</button>;
}
