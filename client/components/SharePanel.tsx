"use client";

import { useEffect, useRef, useState } from "react";
import { Sheet } from "@/components/Sheet";
import { CARD_SIZES, ShareCard } from "@/components/ShareCard";
import { LEVEL_LABEL, type Report } from "@/lib/report";
import { cardTitle, shareUrl, type PublicCard, type ShareChoices } from "@/lib/share";
import { gatewayFetch } from "@/lib/supabase";
import { INPUT, PRIMARY, SECONDARY } from "@/lib/ui";

const BRAND = "VoiceWire Interview"; // server/share.py BRAND

// Sentences the candidate actually said, short enough for the card (the server re-checks the quote).
function quoteOptions(report: Report): string[] {
  const sentences = report.answers.flatMap((a) => a.answer_text.match(/[^.!?]+[.!?]?/g) ?? []);
  return [...new Set(sentences.map((s) => s.trim()).filter((s) => s.length >= 40 && s.length <= 200))].slice(0, 12);
}

// Mirrors server/share.py public_card, for the live preview before publishing.
function previewCard(report: Report, c: ShareChoices, role: string, seniority: string, date: string): PublicCard {
  const d = report.delivery;
  return {
    brand: BRAND,
    score: report.overall_score ?? null,
    verdict: report.verdict ?? null,
    date: date.slice(0, 10),
    name: c.show_name && c.name.trim() ? c.name.trim() : null,
    role: c.show_role ? role : null,
    level: c.show_role ? (LEVEL_LABEL[seniority] ?? null) : null,
    skills: c.show_skills ? (report.dimensions ?? null) : null,
    delivery: c.show_delivery ? { wpm: d.wpm, fillers_per_min: d.fillers_per_min, avg_answer_s: d.avg_answer_s ?? null } : null,
    top_strength: c.show_strength ? (report.top_strength ?? null) : null,
    quote: c.quote,
  };
}

// The fixed-size card scaled to whatever width its container has.
function ScaledCard({ card }: { card: PublicCard }) {
  const ref = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0.35);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(([entry]) => setScale(entry.contentRect.width / CARD_SIZES.wide.width));
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={ref} className="relative w-full overflow-hidden rounded-[8px] border border-divider" style={{ aspectRatio: "1200 / 630" }}>
      <div className="absolute left-0 top-0 origin-top-left" style={{ transform: `scale(${scale})` }}>
        <ShareCard card={card} layout="wide" />
      </div>
    </div>
  );
}

export function SharePanel({
  open,
  onClose,
  sessionId,
  report,
  role,
  seniority,
  createdAt,
  suggestedName,
  initial,
}: {
  open: boolean;
  onClose: () => void;
  sessionId: string;
  report: Report;
  role: string;
  seniority: string;
  createdAt: string;
  suggestedName: string;
  initial: { slug: string | null; choices: ShareChoices | null };
}) {
  const [choices, setChoices] = useState<ShareChoices>(
    initial.choices ?? {
      show_name: !!suggestedName,
      name: suggestedName,
      show_role: true,
      show_skills: true,
      show_delivery: true,
      show_strength: true,
      quote: null,
    },
  );
  const [slug, setSlug] = useState<string | null>(initial.slug);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const quotes = quoteOptions(report);
  const card = previewCard(report, choices, role, seniority, createdAt);
  const url = slug ? shareUrl(slug) : null;
  const set = (patch: Partial<ShareChoices>) => setChoices((c) => ({ ...c, ...patch }));

  const act = async (work: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  const publish = () =>
    act(async () => {
      const { slug } = await gatewayFetch<{ slug: string }>(`/sessions/${sessionId}/share`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(choices),
      });
      setSlug(slug);
    });

  const stop = () =>
    act(async () => {
      await gatewayFetch(`/sessions/${sessionId}/share`, { method: "DELETE" });
      setSlug(null);
    });

  const copy = async () => {
    if (!url) return;
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const text = `${cardTitle(card)}. Practiced with ${BRAND}.`;
  const toggle = (key: keyof ShareChoices, label: string) => (
    <label className="flex items-center gap-2 text-sm text-ink">
      <input type="checkbox" checked={!!choices[key]} onChange={(e) => set({ [key]: e.target.checked })} />
      {label}
    </label>
  );

  return (
    <Sheet open={open} onClose={onClose} title="Share your result">
      <div className="space-y-5 overflow-y-auto px-5 py-4">
        <ScaledCard card={card} />

        <fieldset className="space-y-2">
          <legend className="mb-1 text-sm font-semibold text-ink">Show on the card</legend>
          <div className="flex items-center gap-2">
            {toggle("show_name", "Name")}
            {choices.show_name && (
              <input
                aria-label="Name on the card"
                maxLength={40}
                value={choices.name}
                onChange={(e) => set({ name: e.target.value })}
                className={`${INPUT} py-1 text-sm`}
                placeholder="Initials or name"
              />
            )}
          </div>
          {toggle("show_role", "Role and level")}
          {toggle("show_skills", "Skill scores")}
          {toggle("show_delivery", "How you spoke")}
          {toggle("show_strength", "Strongest skill")}
        </fieldset>

        {quotes.length > 0 && (
          <fieldset>
            <legend className="mb-1 text-sm font-semibold text-ink">Highlight quote</legend>
            <div className="space-y-1">
              <label className="flex items-start gap-2 text-sm text-ink">
                <input type="radio" name="quote" checked={!choices.quote} onChange={() => set({ quote: null })} className="mt-1" />
                No quote
              </label>
              {quotes.map((q) => (
                <label key={q} className="flex items-start gap-2 text-sm text-ink">
                  <input type="radio" name="quote" checked={choices.quote === q} onChange={() => set({ quote: q })} className="mt-1" />
                  <span>“{q}”</span>
                </label>
              ))}
            </div>
          </fieldset>
        )}

        <p className="text-xs text-ink-secondary">
          Anyone with the link sees only this card. Your transcript, recording, CV and job description are never shared.
        </p>
        {error && (
          <p role="alert" className="text-sm text-error">
            {error}
          </p>
        )}

        <button onClick={() => void publish()} disabled={busy} className={`${PRIMARY} w-full`}>
          {slug ? "Update shared card" : "Create share link"}
        </button>

        {url && slug && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input readOnly value={url} aria-label="Share link" className={`${INPUT} text-sm`} onFocus={(e) => e.target.select()} />
              <button onClick={() => void copy()} className={SECONDARY}>
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              <a className={SECONDARY} target="_blank" rel="noopener noreferrer" href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`}>
                LinkedIn
              </a>
              <a className={SECONDARY} target="_blank" rel="noopener noreferrer" href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`}>
                X
              </a>
              <a className={SECONDARY} target="_blank" rel="noopener noreferrer" href={`https://wa.me/?text=${encodeURIComponent(`${text} ${url}`)}`}>
                WhatsApp
              </a>
              <a className={SECONDARY} href={`/s/${slug}/card`} download>
                Download image
              </a>
              {typeof navigator !== "undefined" && "share" in navigator && (
                <button onClick={() => void navigator.share({ title: cardTitle(card), text, url }).catch(() => {})} className={SECONDARY}>
                  More…
                </button>
              )}
            </div>
            <button onClick={() => void stop()} disabled={busy} className="text-sm text-ink-secondary hover:text-error">
              Stop sharing (the link stops working)
            </button>
          </div>
        )}
      </div>
    </Sheet>
  );
}
