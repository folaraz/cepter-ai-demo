import * as React from 'react';
import { cx } from './cx';
import './Cards.css';

export interface TestimonialCardProps extends React.HTMLAttributes<HTMLElement> {
  /** The quote, set in the light display serif. */
  quote: React.ReactNode;
  /** Author name. */
  author: React.ReactNode;
  /** Author title / company. */
  authorRole?: React.ReactNode;
  /** Avatar (usually <VoiceIcon initials=…>). */
  avatar?: React.ReactNode;
  /** Company wordmark or name shown at the right of the author row. */
  logo?: React.ReactNode;
}

/** White quote card, 32px padding, serif quote with author row. */
export function TestimonialCard({ quote, author, authorRole, avatar, logo, className, ...rest }: TestimonialCardProps) {
  return (
    <figure className={cx('cx-testimonial', className)} style={{ margin: 0 }} {...rest}>
      <blockquote className="cx-testimonial__quote">{quote}</blockquote>
      <figcaption className="cx-testimonial__author">
        {avatar}
        <div>
          <div className="cx-testimonial__name">{author}</div>
          {authorRole && <div className="cx-testimonial__role">{authorRole}</div>}
        </div>
        {logo && <div className="cx-testimonial__logo">{logo}</div>}
      </figcaption>
    </figure>
  );
}
