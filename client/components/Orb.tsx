"use client";

import { useEffect, useRef } from "react";
import type { OrbState } from "@/lib/ws";

type DisplayState = OrbState | "disconnected" | "connecting";

type RGB = [number, number, number];

interface OrbConfig {
  sky: [RGB, RGB, RGB]; // sphere gradient: top-light, mid, bottom-edge
  cloudAlpha: number; // how opaque the white clouds read
  flow: number; // how fast clouds drift across the sphere (radii/sec)
  pulse: number; // how much the sphere swells with audio level
}

// ChatGPT voice-mode orb in teal: a sphere with soft white clouds drifting through it, which
// swells with the live audio level (mic while you talk, playback while it replies). All values
// ease toward the active state's config every frame, so state changes blend instead of jumping.
// "disconnected" is the deliberate neutral-gray "off" state.
const STATE_CONFIG: Record<DisplayState, OrbConfig> = {
  idle: { sky: [hex("#e0f7fa"), hex("#80cbc4"), hex("#4db6ac")], cloudAlpha: 0.6, flow: 0.06, pulse: 0.1 },
  listening: { sky: [hex("#e0f7fa"), hex("#4db6ac"), hex("#00897b")], cloudAlpha: 0.7, flow: 0.09, pulse: 0.22 },
  thinking: { sky: [hex("#b2dfdb"), hex("#26a69a"), hex("#00695c")], cloudAlpha: 0.55, flow: 0.2, pulse: 0.05 },
  speaking: { sky: [hex("#e0f7fa"), hex("#26a69a"), hex("#00897b")], cloudAlpha: 0.75, flow: 0.11, pulse: 0.22 },
  connecting: { sky: [hex("#e0f7fa"), hex("#4db6ac"), hex("#00897b")], cloudAlpha: 0.5, flow: 0.14, pulse: 0 },
  disconnected: { sky: [hex("#f5f5f5"), hex("#d8d8d8"), hex("#a8a8a8")], cloudAlpha: 0.45, flow: 0.02, pulse: 0 },
};

// Fixed cloud puffs: x phase (wraps horizontally), y offset, size, wobble phase — all in sphere radii.
const PUFFS = [
  [0.0, -0.45, 0.45, 0.3],
  [0.8, -0.15, 0.55, 1.7],
  [1.7, 0.25, 0.5, 2.9],
  [2.5, 0.55, 0.6, 4.1],
  [3.3, -0.05, 0.4, 5.3],
  [0.4, 0.4, 0.35, 0.9],
  [1.2, 0.7, 0.45, 3.5],
  [3.9, -0.6, 0.35, 2.2],
] as const;
// Horizontal travel span in radii: wide enough that a puff (up to ~0.85R half-width) is fully
// outside the sphere before it wraps, so clouds never pop in or out on the visible face.
const WRAP = 4.6;

export function Orb({
  state,
  interruptTick,
  getLevel,
  getMicLevel,
  size = 240,
}: {
  state: DisplayState;
  size?: number;
  interruptTick?: number;
  getLevel?: () => number;
  getMicLevel?: () => number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef<DisplayState>(state);
  stateRef.current = state;
  const levelFnRef = useRef(getLevel);
  levelFnRef.current = getLevel;
  const micLevelFnRef = useRef(getMicLevel);
  micLevelFnRef.current = getMicLevel;
  const flashRef = useRef(0); // 0 = no flash; 1 = just fired, decays to 0

  useEffect(() => {
    if (interruptTick) flashRef.current = 1;
  }, [interruptTick]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const motionScale = reduceMotion ? 0.2 : 1;

    let t = 0;
    let flowPhase = 0; // integrated, so speed changes never make clouds jump
    let spin = 0;
    let level = 0; // smoothed audio level
    let micLevel = 0; // smoothed mic-only level, for the "you're being heard" ring
    let last = performance.now();
    let raf = 0;
    // live config, eased toward the target state's config each frame
    const cfg: OrbConfig = structuredClone(STATE_CONFIG[stateRef.current]);

    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000); // real time, clamped after tab-switch stalls
      last = now;
      const cx = size / 2;
      const cy = size / 2;
      const current = stateRef.current;
      const goal = STATE_CONFIG[current];
      const ease = 1 - Math.exp(-dt * 3); // ~0.3s blend between states, frame-rate independent
      for (let i = 0; i < 3; i++) for (let c = 0; c < 3; c++) cfg.sky[i][c] += (goal.sky[i][c] - cfg.sky[i][c]) * ease;
      cfg.cloudAlpha += (goal.cloudAlpha - cfg.cloudAlpha) * ease;
      cfg.flow += (goal.flow - cfg.flow) * ease;
      cfg.pulse += (goal.pulse - cfg.pulse) * ease;
      const baseR = size * 0.36;

      const target = current === "disconnected" ? 0 : (levelFnRef.current?.() ?? 0);
      const k = target > level ? 12 : 3; // fast attack, slow release
      level += (target - level) * (1 - Math.exp(-dt * k));
      const breathe = 1 + 0.015 * Math.sin(t * 1.2); // tiny idle breath so it never looks frozen
      const R = baseR * (breathe + level * cfg.pulse * motionScale);

      ctx.clearRect(0, 0, size, size);

      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.clip();

      // sky: lighter at the top, deeper blue toward the bottom edge
      const sky = ctx.createLinearGradient(cx, cy - R, cx, cy + R);
      sky.addColorStop(0, rgba(cfg.sky[0], 1));
      sky.addColorStop(0.45, rgba(cfg.sky[1], 1));
      sky.addColorStop(1, rgba(cfg.sky[2], 1));
      ctx.fillStyle = sky;
      ctx.fillRect(cx - R, cy - R, R * 2, R * 2);

      // clouds: soft white puffs drifting sideways, wrapping off-face; faster flow while talking.
      // Softness comes from the gradient falloff alone — no canvas blur filter, which is costly
      // per frame (dropped frames = stutter) and unsupported in Safari.
      flowPhase += dt * (cfg.flow + level * 0.1) * motionScale;
      for (const [phase, y, puffSize, wob] of PUFFS) {
        const x = ((phase + flowPhase) % WRAP) - WRAP / 2;
        const px = cx + x * R;
        const py = cy + (y + 0.06 * Math.sin(t * 0.6 + wob)) * R;
        const pr = puffSize * R * (1 + 0.08 * Math.sin(t * 0.9 + wob));
        const g = ctx.createRadialGradient(px, py, 0, px, py, pr);
        g.addColorStop(0, rgba(WHITE, cfg.cloudAlpha));
        g.addColorStop(0.35, rgba(WHITE, cfg.cloudAlpha * 0.7));
        g.addColorStop(0.7, rgba(WHITE, cfg.cloudAlpha * 0.25));
        g.addColorStop(1, rgba(WHITE, 0));
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.ellipse(px, py, pr * 1.4, pr, 0, 0, Math.PI * 2);
        ctx.fill();
      }

      // soft inner rim shade so it reads as a sphere, not a flat disc
      const rim = ctx.createRadialGradient(cx, cy, R * 0.7, cx, cy, R);
      rim.addColorStop(0, "rgba(0, 60, 50, 0)");
      rim.addColorStop(1, "rgba(0, 60, 50, 0.12)");
      ctx.fillStyle = rim;
      ctx.fillRect(cx - R, cy - R, R * 2, R * 2);

      ctx.restore();

      // mic ring: reacts only to the user's voice, so "I'm being heard" reads separately from the
      // sphere swelling with the reply. Capped inside the canvas.
      const mic = current === "disconnected" ? 0 : (micLevelFnRef.current?.() ?? 0);
      micLevel += (mic - micLevel) * (1 - Math.exp(-dt * (mic > micLevel ? 14 : 4)));
      if (micLevel > 0.02) {
        const lineWidth = 2 + micLevel * 3;
        ctx.beginPath();
        ctx.arc(cx, cy, Math.min(R * 1.08 + micLevel * baseR * 0.18, size / 2 - lineWidth), 0, Math.PI * 2);
        ctx.strokeStyle = rgba(cfg.sky[1], Math.min(0.9, micLevel * 1.5));
        ctx.lineWidth = lineWidth;
        ctx.stroke();
      }

      if (current === "connecting" && !reduceMotion) {
        spin += dt * 5;
        ctx.beginPath();
        ctx.arc(cx, cy, baseR * 1.15, spin, spin + Math.PI * 1.4);
        ctx.strokeStyle = rgba(cfg.sky[2], 1);
        ctx.lineWidth = 3;
        ctx.lineCap = "round";
        ctx.stroke();
      }

      // barge-in flash: brief expanding ring so an interrupt reads as a visible event
      if (flashRef.current > 0) {
        const progress = 1 - flashRef.current;
        ctx.beginPath();
        ctx.arc(cx, cy, R * (1.1 + progress * 0.25), 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(29, 29, 31, ${0.4 * flashRef.current})`;
        ctx.lineWidth = 2;
        ctx.stroke();
        flashRef.current = reduceMotion ? 0 : Math.max(0, flashRef.current - dt * 2.5);
      }

      t += dt;
      raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [size]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: size, height: size }}
      aria-label={`voice agent state: ${state}`}
    />
  );
}

const WHITE: RGB = [255, 255, 255];

function hex(h: string): RGB {
  return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
}

function rgba([r, g, b]: RGB, alpha: number): string {
  return `rgba(${r | 0}, ${g | 0}, ${b | 0}, ${alpha})`;
}
