/** Joins class names, skipping falsy values. */
export const cn = (...parts: unknown[]) => parts.filter((p) => typeof p === 'string' && p).join(' ');
