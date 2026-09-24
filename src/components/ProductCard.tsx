import * as React from 'react';
import { cx } from './cx';
import './Cards.css';

export interface ProductCardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
  /** Edge-to-edge media area (image, <GradientOrb>, UI mock). 16:10 by default. */
  media?: React.ReactNode;
  /** CSS aspect-ratio for the media area. */
  mediaAspect?: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
}

/** Product preview card: no padding around the media - it fills the card edge to edge - with a caption body below. */
export function ProductCard({ media, mediaAspect, title, description, className, children, ...rest }: ProductCardProps) {
  return (
    <div className={cx('cx-product-card', className)} {...rest}>
      {media && <div className="cx-product-card__media" style={mediaAspect ? { aspectRatio: mediaAspect } : undefined}>{media}</div>}
      {(title || description || children) && (
        <div className="cx-product-card__body">
          {title && <h3 className="cx-title-sm">{title}</h3>}
          {description && <p className="cx-product-card__description">{description}</p>}
          {children}
        </div>
      )}
    </div>
  );
}

export interface ProductCardStackProps extends React.HTMLAttributes<HTMLDivElement> {
  /** ProductCards; the LAST child sits in front, earlier ones fan out behind it. */
  children: React.ReactNode;
}

/** Layers ProductCards into a receding stack (up to ~4 visible). */
export function ProductCardStack({ className, ...rest }: ProductCardStackProps) {
  return <div className={cx('cx-card-stack', className)} {...rest} />;
}
