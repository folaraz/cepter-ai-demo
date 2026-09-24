import * as React from 'react';
import { cx } from './cx';
import './AudioWaveformCard.css';

export interface AudioWaveformCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Voice or clip name. */
  voiceName: React.ReactNode;
  /** Secondary line, e.g. "British · Narration". */
  detail?: React.ReactNode;
  /** Leading avatar (usually <VoiceIcon>). */
  icon?: React.ReactNode;
  /** Clip length label, e.g. "0:42". */
  duration?: string;
  /** 0-1 playback progress; bars before it render in ink. */
  progress?: number;
  /** Shows a pause glyph instead of play. */
  playing?: boolean;
  /** Called when the play/pause button is pressed. */
  onPlayToggle?: () => void;
  /** Seed for the deterministic waveform shape. */
  seed?: number;
  /** Number of bars (default 48). */
  bars?: number;
  /** Tags row under the player (e.g. <Badge shape="tag">). */
  tags?: React.ReactNode;
}

function waveHeights(count: number, seed: number): number[] {
  let s = seed * 9301 + 49297;
  const out: number[] = [];
  for (let i = 0; i < count; i++) {
    s = (s * 9301 + 49297) % 233280;
    const r = s / 233280;
    const env = Math.sin((i / (count - 1)) * Math.PI) * 0.6 + 0.4;
    out.push(Math.max(0.12, Math.min(1, env * (0.35 + r * 0.75))));
  }
  return out;
}

const PlayIcon = () => (<svg viewBox="0 0 14 14" fill="currentColor"><path d="M3 1.5v11l9.5-5.5z" /></svg>);
const PauseIcon = () => (<svg viewBox="0 0 14 14" fill="currentColor"><rect x="2.5" y="1.5" width="3.2" height="11" rx="1" /><rect x="8.3" y="1.5" width="3.2" height="11" rx="1" /></svg>);

/** Voice sample card: avatar + name, ink play button, deterministic waveform and duration. */
export function AudioWaveformCard({ voiceName, detail, icon, duration, progress = 0, playing, onPlayToggle, seed = 7, bars = 48, tags, className, ...rest }: AudioWaveformCardProps) {
  const heights = React.useMemo(() => waveHeights(bars, seed), [bars, seed]);
  const playedUpTo = Math.round(Math.max(0, Math.min(1, progress)) * bars);
  return (
    <div className={cx('cx-wave-card', className)} {...rest}>
      <div className="cx-wave-card__head">
        {icon}
        <div className="cx-wave-card__meta">
          <span className="cx-wave-card__name">{voiceName}</span>
          {detail && <span className="cx-wave-card__detail">{detail}</span>}
        </div>
      </div>
      <div className="cx-wave-card__player">
        <button type="button" className="cx-play" aria-label={playing ? 'Pause' : 'Play'} onClick={onPlayToggle}>
          {playing ? <PauseIcon /> : <PlayIcon />}
        </button>
        <div className="cx-wave" aria-hidden>
          {heights.map((h, i) => (
            <span key={i} className={cx('cx-wave__bar', i < playedUpTo && 'cx-wave__bar--played')} style={{ height: `${Math.round(h * 100)}%` }} />
          ))}
        </div>
        {duration && <span className="cx-wave-card__time">{duration}</span>}
      </div>
      {tags && <div className="cx-wave-card__tags">{tags}</div>}
    </div>
  );
}
