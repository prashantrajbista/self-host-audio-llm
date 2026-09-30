// The share card, written for Satori (next/og ImageResponse) so the same JSX renders the web preview,
// the public page and the PNGs: inline styles only, display:flex on every element with several
// children, fixed colours (images can't read the CSS theme variables; these are the light theme's).
import { humanize } from "@/lib/report";
import type { PublicCard } from "@/lib/share";

const C = {
  bg: "#F5F5F7",
  surface: "#FFFFFF",
  ink: "#1D1D1F",
  inkSecondary: "#6E6E73",
  divider: "#D2D2D7",
  primary: "#00695C",
  primarySoft: "#E0F0EE",
};

export const CARD_SIZES = {
  wide: { width: 1200, height: 630 }, // link previews
  tall: { width: 1080, height: 1350 }, // downloadable post image
} as const;

function Skills({ skills, compact }: { skills: Record<string, number>; compact: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: compact ? 14 : 16, width: "100%" }}>
      {Object.entries(skills)
        .slice(0, 5)
        .map(([name, value]) => (
          <div key={name} style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: compact ? 22 : 26, color: C.ink }}>
              <span>{humanize(name)}</span>
              <span style={{ color: C.inkSecondary }}>{`${value.toFixed(1)}/5`}</span>
            </div>
            <div style={{ display: "flex", height: compact ? 10 : 12, borderRadius: 7, background: C.bg }}>
              <div style={{ display: "flex", width: `${(value / 5) * 100}%`, borderRadius: 7, background: C.primary }} />
            </div>
          </div>
        ))}
    </div>
  );
}

function Stat({ label, value, compact }: { label: string; value: string; compact: boolean }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{ fontSize: compact ? 18 : 24, color: C.inkSecondary }}>{label}</span>
      <span style={{ fontSize: compact ? 30 : 36, fontWeight: 700, color: C.ink }}>{value}</span>
    </div>
  );
}

export function ShareCard({ card, layout }: { card: PublicCard; layout: keyof typeof CARD_SIZES }) {
  const wide = layout === "wide";
  const { width, height } = CARD_SIZES[layout];
  const who = [card.name, card.level && card.role ? `${card.level} ${card.role}` : card.role].filter(Boolean).join(" · ");

  const headline = (
    <div style={{ display: "flex", flexDirection: "column", gap: wide ? 10 : 16 }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: wide ? 150 : 170, fontWeight: 700, color: C.ink, lineHeight: 1 }}>{card.score}</span>
        <span style={{ fontSize: wide ? 44 : 60, color: C.inkSecondary }}>/100</span>
      </div>
      <div style={{ display: "flex" }}>
        <span
          style={{
            fontSize: wide ? 30 : 40,
            fontWeight: 700,
            color: C.primary,
            background: C.primarySoft,
            borderRadius: 999,
            padding: wide ? "6px 22px" : "8px 30px",
          }}
        >
          {card.verdict}
        </span>
      </div>
      {who && <span style={{ fontSize: wide ? 30 : 40, fontWeight: 700, color: C.ink, marginTop: 8 }}>{who}</span>}
      {card.top_strength && (
        <span style={{ fontSize: wide ? 24 : 32, color: C.inkSecondary }}>
          {`Strongest at ${humanize(card.top_strength).toLowerCase()}`}
        </span>
      )}
    </div>
  );

  const details = (
    <div style={{ display: "flex", flexDirection: "column", gap: wide ? 24 : 32, width: "100%" }}>
      {card.skills && <Skills skills={card.skills} compact={wide} />}
      {card.delivery && (
        <div style={{ display: "flex", gap: wide ? 36 : 60 }}>
          <Stat label="Pace" value={`${card.delivery.wpm} wpm`} compact={wide} />
          <Stat label="Fillers" value={`${card.delivery.fillers_per_min}/min`} compact={wide} />
          {card.delivery.avg_answer_s !== null && (
            <Stat label="Avg answer" value={`${Math.round(card.delivery.avg_answer_s)}s`} compact={wide} />
          )}
        </div>
      )}
    </div>
  );

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        width,
        height,
        padding: wide ? 56 : 72,
        background: C.surface,
        borderTop: `${wide ? 12 : 16}px solid ${C.primary}`,
        fontFamily: "sans-serif",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", flexDirection: wide ? "row" : "column", gap: wide ? 64 : 44, width: "100%" }}>
        <div style={{ display: "flex", flexDirection: "column", width: wide ? 460 : "100%", flexShrink: 0 }}>{headline}</div>
        {(card.skills || card.delivery) && (
          // wide: fills the right column; tall: natural height (flex:1 in a column collapses it to zero)
          <div style={wide ? { display: "flex", flex: 1 } : { display: "flex", width: "100%" }}>{details}</div>
        )}
      </div>

      {card.quote && (
        <div
          style={{
            display: "flex",
            fontSize: wide ? 26 : 36,
            fontStyle: "italic",
            color: C.ink,
            background: C.bg,
            borderRadius: 16,
            padding: wide ? "16px 22px" : "22px 30px",
            marginTop: 24,
            flexShrink: 0,
          }}
        >
          {`“${card.quote}”`}
        </div>
      )}

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontSize: wide ? 22 : 30,
          color: C.inkSecondary,
          borderTop: `2px solid ${C.divider}`,
          paddingTop: wide ? 16 : 24,
          marginTop: 24,
          flexShrink: 0,
        }}
      >
        <span style={{ fontWeight: 700, color: C.primary }}>{`Mock interview · ${card.brand}`}</span>
        <span>{card.date}</span>
      </div>
    </div>
  );
}
