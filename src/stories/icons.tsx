import * as React from 'react';

const base = { viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };
export const MicIcon = () => (<svg {...base}><rect x="9" y="3" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>);
export const WaveIcon = () => (<svg {...base}><path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 11v2" /></svg>);
export const GlobeIcon = () => (<svg {...base}><circle cx="12" cy="12" r="9" /><path d="M3 12h18M12 3c2.5 3 2.5 15 0 18M12 3c-2.5 3-2.5 15 0 18" /></svg>);
export const BotIcon = () => (<svg {...base}><rect x="4" y="8" width="16" height="11" rx="3" /><path d="M12 4v4M9 13h.01M15 13h.01" /></svg>);
export const ArrowRight = () => (<svg {...base}><path d="M5 12h14M13 6l6 6-6 6" /></svg>);
export const SearchIcon = () => (<svg {...base}><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></svg>);
export const PlayIcon = () => (<svg viewBox="0 0 24 24" fill="currentColor"><path d="M7 4.5v15l12.5-7.5z" /></svg>);
