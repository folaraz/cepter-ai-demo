import * as React from 'react';
import { cx } from './cx';
import './Voice.css';

export interface VoiceIconProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** 1-2 letters shown in the circle. */
  initials?: string;
  /** Image URL (overrides initials). */
  src?: string;
  /** Glyph to show instead of initials. */
  icon?: React.ReactNode;
  /** Diameter in px (default 32). */
  size?: number;
  /** Plain warm-grey plate (default) or a soft pastel wash. */
  tone?: 'default' | 'mint' | 'peach' | 'lavender' | 'sky' | 'rose';
}

/** Circular voice avatar / icon plate - warm grey, fully rounded. */
export function VoiceIcon({ initials, src, icon, size = 32, tone = 'default', className, style, ...rest }: VoiceIconProps) {
  return (
    <span className={cx('cx-voice-icon', tone !== 'default' && `cx-voice-icon--${tone}`, className)} style={{ width: size, height: size, fontSize: Math.round(size * 0.38), ...style }} {...rest}>
      {src ? <img src={src} alt="" /> : icon ?? initials}
    </span>
  );
}
