import * as React from 'react';
import { cx } from './cx';
import './Footer.css';

export interface FooterLinkProps extends React.AnchorHTMLAttributes<HTMLAnchorElement> {}

/** Plain body-sm link used in footer columns. */
export function FooterLink({ className, href = '#', ...rest }: FooterLinkProps) {
  return <a className={cx('cx-footer-link', className)} href={href} {...rest} />;
}

export interface FooterColumn {
  title: string;
  links: Array<{ label: string; href?: string }>;
}

export interface FooterProps extends React.HTMLAttributes<HTMLElement> {
  /** Wordmark. Default "cepter ai demo". */
  brand?: React.ReactNode;
  /** Short line under the wordmark. */
  tagline?: React.ReactNode;
  /** Link columns (5 at desktop by design). */
  columns?: FooterColumn[];
  /** Bottom-left legal text. */
  legal?: React.ReactNode;
  /** Bottom-right slot (social links, locale). */
  bottomRight?: React.ReactNode;
}

/** Closing footer: wordmark + tagline, up to 5 uppercase-headed link columns, legal row. */
export function Footer({ brand = 'cepter ai demo', tagline, columns = [], legal, bottomRight, className, style, ...rest }: FooterProps) {
  return (
    <footer className={cx('cx-footer', className)} style={{ ['--cx-footer-cols' as string]: Math.max(1, columns.length), ...style }} {...rest}>
      <div className="cx-footer__inner">
        <div className="cx-footer__top">
          <div className="cx-footer__brand">
            <span className="cx-footer__wordmark">{brand}</span>
            {tagline && <p className="cx-footer__tagline">{tagline}</p>}
          </div>
          {columns.map((col) => (
            <div key={col.title} className="cx-footer__col">
              <h4 className="cx-footer__heading">{col.title}</h4>
              <ul className="cx-footer__list">
                {col.links.map((l) => (<li key={l.label}><FooterLink href={l.href}>{l.label}</FooterLink></li>))}
              </ul>
            </div>
          ))}
        </div>
        {(legal || bottomRight) && (
          <div className="cx-footer__bottom">
            <span>{legal}</span>
            {bottomRight && <span>{bottomRight}</span>}
          </div>
        )}
      </div>
    </footer>
  );
}
