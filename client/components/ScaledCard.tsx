"use client";

import { useEffect, useRef, useState } from "react";
import { CARD_SIZES, ShareCard } from "@/components/ShareCard";
import type { PublicCard } from "@/lib/share";

// The fixed-size card scaled to whatever width its container has.
export function ScaledCard({ card }: { card: PublicCard }) {
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

