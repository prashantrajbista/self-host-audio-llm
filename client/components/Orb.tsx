"use client";

import { useEffect, useRef } from "react";
import type { OrbState } from "@/lib/ws";

type DisplayState = OrbState | "disconnected";

const STATE_COLORS: Record<DisplayState, { core: string; glow: string }> = {
  idle: { core: "#6b7280", glow: "rgba(107, 114, 128, 0.35)" },
  listening: { core: "#3b82f6", glow: "rgba(59, 130, 246, 0.45)" },
  thinking: { core: "#f59e0b", glow: "rgba(245, 158, 11, 0.45)" },
  speaking: { core: "#22c55e", glow: "rgba(34, 197, 94, 0.45)" },
  disconnected: { core: "#374151", glow: "rgba(55, 65, 81, 0.25)" },
};

export function Orb({ state }: { state: DisplayState }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<DisplayState>(state);
  stateRef.current = state;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let phase = 0;
    let raf = 0;

    const tick = () => {
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const current = stateRef.current;
      const colors = STATE_COLORS[current];

      ctx.clearRect(0, 0, w, h);

      phase += current === "idle" || current === "disconnected" ? 0.015 : 0.06;
      const pulse = 1 + 0.1 * Math.sin(phase);
      const baseRadius = Math.min(w, h) * 0.22 * pulse;

      const glowRadius = baseRadius * 2.2;
      const glow = ctx.createRadialGradient(cx, cy, baseRadius * 0.3, cx, cy, glowRadius);
      glow.addColorStop(0, colors.glow);
      glow.addColorStop(1, "rgba(0, 0, 0, 0)");
      ctx.fillStyle = glow;
      ctx.fillRect(0, 0, w, h);

      const core = ctx.createRadialGradient(
        cx - baseRadius * 0.3,
        cy - baseRadius * 0.3,
        baseRadius * 0.1,
        cx,
        cy,
        baseRadius,
      );
      core.addColorStop(0, "#ffffff");
      core.addColorStop(0.25, colors.core);
      core.addColorStop(1, colors.core);

      ctx.beginPath();
      ctx.arc(cx, cy, baseRadius, 0, Math.PI * 2);
      ctx.fillStyle = core;
      ctx.shadowColor = colors.glow;
      ctx.shadowBlur = baseRadius * 0.8;
      ctx.fill();
      ctx.shadowBlur = 0;

      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      width={240}
      height={240}
      className="rounded-full"
      aria-label={`voice agent state: ${state}`}
    />
  );
}
