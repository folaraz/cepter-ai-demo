import * as React from 'react';
import { cx } from './cx';
import './TextInput.css';

export interface TextInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  /** Visible label above the field. */
  label?: React.ReactNode;
  /** Helper text below the field. Replaced by `error` when set. */
  hint?: React.ReactNode;
  /** Error message; turns the border red. */
  error?: React.ReactNode;
  /** Leading icon inside the field (e.g. search glyph). */
  icon?: React.ReactNode;
}

/** 44px text field, 8px radius, hairline-strong border that thickens to 2px ink on focus. */
export const TextInput = React.forwardRef<HTMLInputElement, TextInputProps>(function TextInput(
  { label, hint, error, icon, id, className, style, ...rest }, ref,
) {
  const autoId = React.useId();
  const inputId = id ?? autoId;
  const message = error ?? hint;
  return (
    <div className={cx('cx-field', error && 'cx-field--error', className)} style={style}>
      {label && <label className="cx-field__label" htmlFor={inputId}>{label}</label>}
      <div className="cx-field__control">
        {icon && <span className="cx-field__icon" aria-hidden>{icon}</span>}
        <input ref={ref} id={inputId} className={cx('cx-input', icon && 'cx-input--with-icon')} aria-invalid={error ? true : undefined} {...rest} />
      </div>
      {message && <span className="cx-field__hint">{message}</span>}
    </div>
  );
});
