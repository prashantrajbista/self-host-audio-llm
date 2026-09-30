// Shared class strings for the interview coach pages (same tokens as the call UI, see DESIGN.md).
const FOCUS = "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";
// pages inside the (app)/(site) layouts: the layout owns min-height, background and font
export const PAGE = "px-4 py-10 motion-safe:animate-fade-in";
const CARD_BASE = "w-full mx-auto rounded-[12px] border border-divider bg-surface p-6 shadow-ambient";
export const CARD = `${CARD_BASE} max-w-lg`;
export const WIDE_CARD = `${CARD_BASE} max-w-2xl`;
export const PRIMARY = `rounded-full px-6 py-2.5 text-[0.9375rem] font-semibold bg-primary hover:bg-primary-hover text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${FOCUS}`;
export const SECONDARY = `rounded-full border border-divider bg-surface px-5 py-2 text-sm text-ink hover:border-primary transition-colors disabled:opacity-50 ${FOCUS}`;
export const INPUT = `w-full rounded-[8px] border border-divider bg-bg px-3 py-2 text-ink placeholder:text-ink-secondary ${FOCUS}`;
export const LABEL = "block text-sm font-semibold text-ink mb-1";
// pages outside the (app)/(site) layouts (sign-in, the live interview) supply their own ground
export const STANDALONE = "min-h-dvh bg-bg font-sans";
