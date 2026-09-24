import * as React from 'react';
import { cx } from './cx';

export type DisplaySize = 'mega' | 'xl' | 'lg' | 'md' | 'sm';
export type TextVariant = 'title-md' | 'title-sm' | 'body-md' | 'body-strong' | 'body-sm' | 'caption' | 'caption-uppercase';
export type TextTone = 'ink' | 'body' | 'muted' | 'on-dark' | 'on-dark-soft';

export interface DisplayProps extends React.HTMLAttributes<HTMLHeadingElement> {
  /** Display scale step. Always rendered at weight 300 in the display serif. */
  size?: DisplaySize;
  /** Element to render. Defaults to h1 for mega/xl, h2 for lg/md, h3 for sm. */
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span' | 'div';
  /** Colour on dark surfaces. */
  tone?: 'ink' | 'on-dark';
}

const defaultHeading: Record<DisplaySize, DisplayProps['as']> = { mega: 'h1', xl: 'h1', lg: 'h2', md: 'h2', sm: 'h3' };

/** Editorial serif headline (weight 300, negative tracking). Never bold. */
export function Display({ size = 'lg', as, tone = 'ink', className, ...rest }: DisplayProps) {
  const Tag = (as ?? defaultHeading[size]) as React.ElementType;
  return <Tag className={cx(`cx-display-${size}`, tone === 'on-dark' && 'cx-tone-on-dark', className)} {...rest} />;
}

export interface TextProps extends React.HTMLAttributes<HTMLElement> {
  /** Inter type role. */
  variant?: TextVariant;
  /** Text colour role. Titles default to ink, everything else to body. */
  tone?: TextTone;
  as?: 'p' | 'span' | 'div' | 'label' | 'h3' | 'h4' | 'h5' | 'strong';
}

/** Body / UI text in Inter with the system's editorial letter-spacing. */
export function Text({ variant = 'body-md', tone, as = 'p', className, ...rest }: TextProps) {
  const Tag = as as React.ElementType;
  return <Tag className={cx(`cx-${variant}`, tone && `cx-tone-${tone}`, className)} {...rest} />;
}
