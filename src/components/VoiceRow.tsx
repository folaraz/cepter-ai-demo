import * as React from 'react';
import { cx } from './cx';
import { VoiceIcon, type VoiceIconProps } from './VoiceIcon';
import './Voice.css';

export interface VoiceRowProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Voice name. */
  name: React.ReactNode;
  /** Accent / description line, e.g. "American · Warm, conversational". */
  accent?: React.ReactNode;
  /** Initials for the default 32px VoiceIcon. */
  initials?: string;
  /** Pastel tone for the default icon. */
  iconTone?: VoiceIconProps['tone'];
  /** Custom leading element (replaces the default VoiceIcon). */
  icon?: React.ReactNode;
  /** Tags (e.g. <Badge shape="tag">) shown before the action; hidden on mobile. */
  tags?: React.ReactNode;
  /** Right-aligned action, e.g. <Button variant="outline" size="sm">Preview</Button>. */
  action?: React.ReactNode;
  /** Highlight as selected. */
  selected?: boolean;
}

/** One row of a voice library list: 32px circular icon, name + accent stack, optional tags and preview action. Stack rows directly - hairlines are built in. */
export function VoiceRow({ name, accent, initials, iconTone, icon, tags, action, selected, className, ...rest }: VoiceRowProps) {
  return (
    <div className={cx('cx-voice-row', selected && 'cx-voice-row--selected', className)} {...rest}>
      {icon ?? <VoiceIcon initials={initials} tone={iconTone} />}
      <div className="cx-voice-row__text">
        <span className="cx-voice-row__name">{name}</span>
        {accent && <span className="cx-voice-row__accent">{accent}</span>}
      </div>
      {tags && <div className="cx-voice-row__tags">{tags}</div>}
      {action && <div className="cx-voice-row__action">{action}</div>}
    </div>
  );
}
