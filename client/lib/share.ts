// Public share cards (server/share.py decides what's in them).

export interface PublicCard {
  brand: string;
  score: number | null;
  verdict: string | null;
  date: string;
  name: string | null;
  role: string | null;
  level: string | null;
  skills: Record<string, number> | null;
  delivery: { wpm: number; fillers_per_min: number; avg_answer_s: number | null } | null;
  top_strength: string | null;
  quote: string | null;
}

export interface ShareChoices {
  show_name: boolean;
  name: string;
  show_role: boolean;
  show_skills: boolean;
  show_delivery: boolean;
  show_strength: boolean;
  quote: string | null;
}

export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/$/, "");

export const shareUrl = (slug: string) => `${SITE_URL}/s/${slug}`;

// Server-side only (public page + image routes): the Next server calling the gateway directly.
export async function fetchCard(slug: string): Promise<PublicCard | null> {
  const base = (process.env.GATEWAY_HTTP_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const res = await fetch(`${base}/share/${encodeURIComponent(slug)}`, { cache: "no-store" }); // revocable: never cache
  return res.ok ? ((await res.json()) as PublicCard) : null;
}

export const cardTitle = (c: PublicCard) =>
  `${c.verdict} · ${c.score}/100 on a mock ${c.role ? `${c.role} ` : ""}interview`;
