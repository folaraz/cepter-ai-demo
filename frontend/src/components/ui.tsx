// Shared primitives. Styling is Tailwind utilities over the design tokens only.
import { forwardRef, type ButtonHTMLAttributes, type CSSProperties, type ReactNode } from 'react';
import type { StatusDef } from '../lib/status';
import { cn } from '../lib/cn';

// ---------------------------------------------------------------- Button

type Tone = 'outline' | 'ink';
type Size = 'md' | 'sm' | 'xs' | 'eval' | 'icon';

const TONES: Record<Tone, string> = {
  outline: 'border-control bg-transparent text-ink hover:not-disabled:not-aria-disabled:bg-surface-strong',
  ink: 'border-primary bg-primary text-on-primary hover:not-disabled:not-aria-disabled:opacity-88',
};
const SIZES: Record<Size, string> = {
  md: 'h-9 px-[18px] text-md',
  sm: 'h-8 px-3.5 text-sm',
  xs: 'h-7 px-2.5 text-sm',
  eval: 'h-[30px] justify-center px-[18px] text-sm',
  icon: 'size-8 justify-center p-0 text-xl',
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** `ink` is the one primary pill per view. */
  tone?: Tone;
  size?: Size;
  /** Share the row equally with sibling buttons. */
  grow?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { tone = 'outline', size = 'md', grow, className, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      data-tone={tone}
      className={cn(
        'group/btn inline-flex items-center gap-2 whitespace-nowrap rounded-pill border font-medium transition-[background-color,opacity] duration-120',
        'disabled:border-hairline disabled:text-disabled',
        TONES[tone],
        SIZES[size],
        grow && 'flex-1 basis-0 justify-center',
        className,
      )}
      {...rest}
    />
  );
});

/** Uppercase text link: "← Summary", "View finding →". */
export function TextLink({ className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        'min-h-6 border-none bg-transparent px-0 py-1 font-body text-xs font-semibold uppercase tracking-label text-ink',
        'underline decoration-transparent underline-offset-3 transition-[text-decoration-color] duration-120 hover:decoration-ink',
        className,
      )}
      {...rest}
    />
  );
}

// ---------------------------------------------------------------- status

/** Decorative status glyph; the word next to it carries the meaning. */
export function Glyph({ children, className, style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <span aria-hidden="true" className={cn('inline-block w-3 shrink-0 text-center font-mono text-xs tracking-none', className)} style={style}>
      {children}
    </span>
  );
}

/** Glyph + word in the status colour. */
export function Tag({ def, small, className, children }: { def: StatusDef; small?: boolean; className?: string; children?: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 whitespace-nowrap font-medium', small ? 'text-xs' : 'text-sm', className)} style={{ color: def.color }}>
      <Glyph>{def.glyph}</Glyph>
      {children ?? def.word}
    </span>
  );
}

/** Result badge: 24px pill, 1px border and 8% tint of the result colour. */
export function ResultPill({ def }: { def: StatusDef }) {
  return (
    <span
      className={cn(
        'relative inline-flex h-6 items-center gap-1.5 whitespace-nowrap rounded-pill border border-current px-2.5 text-sm font-medium',
        "before:pointer-events-none before:absolute before:inset-0 before:rounded-[inherit] before:bg-current before:opacity-8 before:content-['']",
      )}
      style={{ color: def.color }}
    >
      <Glyph>{def.glyph}</Glyph>
      {def.word}
    </span>
  );
}

/** Keyboard cap. Inside an ink button it takes the button's colour. */
export function Kbd({ children, large }: { children: ReactNode; large?: boolean }) {
  return (
    <kbd
      className={cn(
        'inline-flex items-center justify-center rounded-key border border-control px-1 font-mono font-normal leading-none tracking-none text-body',
        'group-data-[tone=ink]/btn:border-current group-data-[tone=ink]/btn:text-current group-data-[tone=ink]/btn:opacity-70',
        large ? 'h-[22px] min-w-[22px] text-xs' : 'h-[18px] min-w-[18px] text-2xs',
      )}
    >
      {children}
    </kbd>
  );
}

// ---------------------------------------------------------------- surfaces

export const panel = 'rounded-card border border-hairline bg-surface';

/** Skeleton bar. */
export function Sk({ className, style }: { className?: string; style?: CSSProperties }) {
  return <span className={cn('block h-[11px] animate-pulse-soft rounded-[3px] bg-surface-strong', className)} style={style} />;
}

/** Row hover used by clickable cells and cards. */
export const hit = 'transition-[background-color] duration-120 hover:bg-surface-strong';

export const srOnly = 'sr-only';
