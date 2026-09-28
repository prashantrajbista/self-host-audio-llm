"use client";

import { useEffect, useRef } from "react";
import type { OrbState } from "@/lib/ws";

type DisplayState = OrbState | "disconnected" | "connecting";

interface OrbConfig {
  base: [string, string, string]; // lit-sphere gradient: highlight, mid, edge
  cloud: [string, string]; // internal soft cloud tones, cycled across cloud layers
  breathSpeed: number; // how fast the internal color comes and goes
  breathMin: number; // cloud opacity floor (never fully vanishes)
  breathMax: number; // cloud opacity ceiling
  driftSpeed: number; // how fast the internal clouds drift within the sphere
}

// A solid sphere with a crisp edge and soft internal cloud-light movement — the ChatGPT
// realtime-orb reference, recolored teal/green. Size stays fixed; only the internal light
// breathes and drifts, which is what "color coming and going while talking" asks for. Clouds
// are blurred but clipped to the circle, so blur never bleeds past the boundary (canvas filters
// are masked by the active clip at fill time). All states share the teal family;
// "disconnected" is the deliberate neutral-gray exception — an "off" state, not a pipeline one.
const STATE_CONFIG: Record<DisplayState, OrbConfig> = {
  idle: {
    base: ["#e0f7fa", "#80cbc4", "#4db6ac"],
    cloud: ["#e0f7fa", "#80cbc4"],
    breathSpeed: 0.5,
    breathMin: 0.15,
    breathMax: 0.4,
    driftSpeed: 0.15,
  },
  listening: {
    base: ["#e0f7fa", "#26a69a", "#00897b"],
    cloud: ["#e0f7fa", "#4db6ac"],
    breathSpeed: 0.9,
    breathMin: 0.2,
    breathMax: 0.65,
    driftSpeed: 0.3,
  },
  thinking: {
    base: ["#b2dfdb", "#00897b", "#004d40"],
    cloud: ["#26a69a", "#00695c"],
    breathSpeed: 1.6,
    breathMin: 0.25,
    breathMax: 0.8,
    driftSpeed: 0.55,
  },
  speaking: {
    base: ["#e0f7fa", "#00bfa5", "#00897b"],
    cloud: ["#e0f7fa", "#26a69a"],
    breathSpeed: 2.2,
    breathMin: 0.2,
    breathMax: 0.95,
    driftSpeed: 0.45,
  },
  connecting: {
    base: ["#e0f7fa", "#26a69a", "#00897b"],
    cloud: ["#e0f7fa", "#4db6ac"],
    breathSpeed: 1.2,
    breathMin: 0.2,
    breathMax: 0.6,
    driftSpeed: 0.4,
  },
  disconnected: {
    base: ["#f5f5f5", "#d8d8d8", "#a8a8a8"],
    cloud: ["#f0f0f0", "#c9c9c9"],
    breathSpeed: 0.2,
    breathMin: 0.1,
    breathMax: 0.2,
    driftSpeed: 0.05,
  },
};

const CLOUD_COUNT = 2;

export function Orb({ state, interruptTick }: { state: DisplayState; interruptTick?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<DisplayState>(state);
  stateRef.current = state;
  const flashRef = useRef(0); // 0 = no flash; 1 = just fired, decays to 0

  useEffect(() => {
    if (interruptTick) flashRef.current = 1;
  }, [interruptTick]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const motionScale = reduceMotion ? 0.2 : 1;

    let t = 0;
    let spin = 0;
    let raf = 0;

    const tick = () => {
      const w = canvas.width;
      const h = canvas.height;
      const cx = w / 2;
      const cy = h / 2;
      const current = stateRef.current;
      const cfg = STATE_CONFIG[current];
      const outerR = Math.min(w, h) * 0.4;

      ctx.clearRect(0, 0, w, h);

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, outerR, 0, Math.PI * 2);
      ctx.clip();

      // base: a lit sphere, highlight offset toward the upper-left like a real lit ball —
      // crisp edge, no blur, gives the sphere its solid form.
      const base = ctx.createRadialGradient(
        cx - outerR * 0.3,
        cy - outerR * 0.35,
        outerR * 0.05,
        cx,
        cy,
        outerR,
      );
      base.addColorStop(0, cfg.base[0]);
      base.addColorStop(0.55, cfg.base[1]);
      base.addColorStop(1, cfg.base[2]);
      ctx.fillStyle = base;
      ctx.fillRect(cx - outerR, cy - outerR, outerR * 2, outerR * 2);

      // internal clouds: soft, blurred, drifting light — clipped to the circle above, so the
      // blur never bleeds past the sphere's edge. Opacity breathes over time, which is the
      // "color coming and going" effect; speed/amplitude come from the state config.
      const breath =
        cfg.breathMin +
        (cfg.breathMax - cfg.breathMin) * (0.5 + 0.5 * Math.sin(t * cfg.breathSpeed * motionScale));

      ctx.filter = `blur(${outerR * 0.35}px)`;
      ctx.globalCompositeOperation = "lighter";
      for (let i = 0; i < CLOUD_COUNT; i++) {
        const drift = t * cfg.driftSpeed * motionScale * (i === 0 ? 1 : -0.7) + i * 2.4;
        const dx = cx + Math.cos(drift) * outerR * 0.35;
        const dy = cy + Math.sin(drift * 1.4) * outerR * 0.3;
        const cloudR = outerR * 0.7;

        const grad = ctx.createRadialGradient(dx, dy, 0, dx, dy, cloudR);
        const alpha = (breath * (i === 0 ? 1 : 0.7)).toFixed(3);
        grad.addColorStop(0, hexToRgba(cfg.cloud[i % cfg.cloud.length], Number(alpha)));
        grad.addColorStop(1, hexToRgba(cfg.cloud[i % cfg.cloud.length], 0));
        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(dx, dy, cloudR, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.filter = "none";
      ctx.globalCompositeOperation = "source-over";

      ctx.restore();

      // connecting: a rotating arc outside the sphere's own edge makes "working" legible as a
      // shape change, since the sphere itself can't carry a fifth distinct read within one hue.
      if (current === "connecting" && !reduceMotion) {
        spin += 0.08;
        ctx.beginPath();
        ctx.arc(cx, cy, outerR * 1.15, spin, spin + Math.PI * 1.4);
        ctx.strokeStyle = "#00897b";
        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.stroke();
      }

      // barge-in flash: a brief expanding ring distinct from the sphere's own breathing, so an
      // interrupt reads as a visible event. Ink-colored for contrast against the white ground
      // and the teal sphere alike.
      if (flashRef.current > 0) {
        const progress = 1 - flashRef.current;
        const ringRadius = outerR * (1.1 + progress * 1.3);
        ctx.beginPath();
        ctx.arc(cx, cy, ringRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(29, 29, 31, ${0.4 * flashRef.current})`;
        ctx.lineWidth = 2;
        ctx.stroke();
        flashRef.current = reduceMotion ? 0 : Math.max(0, flashRef.current - 0.04);
      }

      t += 0.016;
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

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
