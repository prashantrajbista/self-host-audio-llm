// Facts the site states about itself (legal pages, footer, pricing). Change them here, in one place.
// server/share.py BRAND and server/billing PRODUCTS must match the brand and prices.

export const BRAND = "VoiceWire Interview";
export const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";
export const TAGLINE = "Practice interviews with a live AI interviewer and get scored feedback.";
export const OPERATOR = "VoiceWire"; // who sells the service (update to the legal entity or your legal name)
export const JURISDICTION = "Nepal";
export const SUPPORT_EMAIL = "hello@voicewire.tech";
export const LEGAL_UPDATED = "5 October 2026";
export const FREE_MOCKS = 2;
export const RETENTION_DAYS = 30; // deleted items and old recordings are purged after this (server/purge.py)

export const PLANS = [
  {
    name: "Free",
    price: "$0",
    unit: "to start",
    summary: "Try it before you pay.",
    features: [`${FREE_MOCKS} full mock interviews`, "Scored report for each", "Replay and share your results"],
    cta: "Start free",
  },
  {
    name: "5 mocks",
    price: "$9",
    unit: "one-time",
    summary: "Practise across a few applications.",
    features: ["5 full mock interviews", "Credits never expire", "Everything in Free"],
    cta: "Get 5 mocks",
  },
  {
    name: "30-day pass",
    price: "$29",
    unit: "one-time",
    summary: "For an intense stretch of interviews.",
    features: ["Unlimited interviews for 30 days", "No auto-renewal", "Everything in Free"],
    cta: "Get the pass",
  },
];
