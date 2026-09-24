import * as React from 'react';
import { cx } from './cx';
import './GradientOrb.css';

export type OrbColor = 'mint' | 'peach' | 'lavender' | 'sky' | 'rose';

export interface GradientOrbProps extends React.HTMLAttributes<HTMLDivElement> {
  /** One of the five pastel atmospheric stops. */
  color?: OrbColor;
  /** Diameter in px. */
  size?: number;
  /** Centre position inside the positioned parent (any CSS length, default 50%). */
  x?: string;
  y?: string;
}

/**
 * Soft blurred radial bloom - pure atmosphere, never a surface.
 * Place inside a `position: relative; overflow: hidden` parent and keep content above it (z-index 1).
 */
export function GradientOrb({ color = 'lavender', size = 480, x = '50%', y = '50%', className, style, ...rest }: GradientOrbProps) {
  return <div aria-hidden className={cx('cx-orb', `cx-orb--${color}`, className)} style={{ width: size, height: size, left: x, top: y, ...style }} {...rest} />;
}
