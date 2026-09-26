// Shared primitives. Styling is Tailwind utilities over the design tokens only.
import { forwardRef, type ButtonHTMLAttributes, type CSSProperties, type ReactNode } from 'react';
import type { LucideIcon } from 'lucide-react';
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

/** Quiet inline link-button: "View finding". */
export function TextLink({ className, ...rest }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={cn(
        'inline-flex min-h-6 items-center gap-1 border-none bg-transparent px-0 py-1 text-md font-medium text-ink',
        'underline decoration-hairline underline-offset-4 transition-[text-decoration-color] duration-120 hover:decoration-ink',
        className,
      )}
      {...rest}
    />
  );
}

// ---------------------------------------------------------------- status

/** Decorative icon sized to sit on the text baseline; the word next to it carries the meaning. */
export function Icon({
  icon: I,
  size = 13,
  filled,
  spin,
  className,
  style,
}: {
  icon: LucideIcon;
  size?: number;
  filled?: boolean;
  spin?: boolean;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <I
      aria-hidden="true"
      focusable="false"
      size={size}
      strokeWidth={filled ? 0 : 2}
      fill={filled ? 'currentColor' : 'none'}
      className={cn('shrink-0', spin && 'animate-spin', className)}
      style={style}
    />
  );
}

/** Icon + word in the status colour. */
export function Tag({ def, small, className, children }: { def: StatusDef; small?: boolean; className?: string; children?: ReactNode }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 whitespace-nowrap font-medium', small ? 'text-xs' : 'text-sm', className)} style={{ color: def.color }}>
      <Icon icon={def.icon} filled={def.filled} spin={def.spin} size={def.filled ? (small ? 8 : 9) : small ? 12 : 13} />
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
      <Icon icon={def.icon} size={13} />
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

// ---------------------------------------------------------------- structure

/** Small neutral count, e.g. next to a heading or nav item. */
export function Count({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex h-5 min-w-5 items-center justify-center rounded-pill bg-surface-strong px-1.5 text-xs font-medium text-body tabular-nums',
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Section heading: sentence case, optional count, optional one-line description and trailing slot. */
export function SectionHeading({
  id,
  title,
  count,
  description,
  children,
  as: H = 'h2',
  className,
}: {
  id?: string;
  title: ReactNode;
  count?: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  as?: 'h2' | 'h3';
  className?: string;
}) {
  return (
    <div className={cn('flex flex-wrap items-baseline gap-x-3 gap-y-0.5', className)}>
      <H id={id} className="flex items-center gap-2 text-lg font-semibold tracking-tight text-ink">
        {title}
        {count !== undefined && <Count>{count}</Count>}
      </H>
      {description && <p className="text-sm text-muted">{description}</p>}
      {children && <div className="ml-auto flex items-center gap-2">{children}</div>}
    </div>
  );
}

/** Square icon-only button. Always pass an aria-label; the title doubles as the tooltip. */
export const IconButton = forwardRef<HTMLButtonElement, ButtonHTMLAttributes<HTMLButtonElement> & { icon: LucideIcon; size?: 'sm' | 'md' }>(
  function IconButton({ icon, size = 'md', className, title, type = 'button', ...rest }, ref) {
    return (
      <button
        ref={ref}
        type={type}
        title={title ?? rest['aria-label']}
        className={cn(
          'inline-flex shrink-0 items-center justify-center rounded-pill border border-control bg-transparent text-ink transition-[background-color] duration-120',
          'hover:not-disabled:bg-surface-strong disabled:border-hairline disabled:text-disabled',
          size === 'md' ? 'size-8' : 'size-7',
          className,
        )}
        {...rest}
      >
        <Icon icon={icon} size={size === 'md' ? 16 : 15} />
      </button>
    );
  },
);

/** The DataRoom Lens mark: two overlapping circles whose intersection forms a lens. */
export function BrandMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 22 22" aria-hidden="true" focusable="false" className="shrink-0">
      <defs>
        <clipPath id="lens-left">
          <circle cx="8.5" cy="11" r="5" />
        </clipPath>
      </defs>
      <rect width="22" height="22" rx="6" fill="var(--primary)" />
      <circle cx="8.5" cy="11" r="5" fill="none" stroke="var(--on-primary)" strokeWidth="1.4" opacity="0.55" />
      <circle cx="13.5" cy="11" r="5" fill="none" stroke="var(--on-primary)" strokeWidth="1.4" opacity="0.55" />
      <circle cx="13.5" cy="11" r="5" fill="var(--on-primary)" clipPath="url(#lens-left)" />
    </svg>
  );
}
