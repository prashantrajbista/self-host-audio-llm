"use client";

import { useEffect, useRef, useState } from "react";
import { audioLevel } from "@/lib/audio";
import { AlertIcon, CheckIcon, MicIcon } from "@/components/Icons";

type Phase = "idle" | "asking" | "listening" | "heard" | "blocked" | "missing";
const HEARD_LEVEL = 0.12; // normal speech clears this easily; room noise doesn't

// Asks for the mic and shows a live level meter until the user's voice is heard. The stream is released
// on unmount: the call opens its own when it starts.
export function MicCheck({ onReady }: { onReady: (ready: boolean) => void }) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [level, setLevel] = useState(0);
  const cleanup = useRef<() => void>(() => {});

  useEffect(() => () => cleanup.current(), []);
  useEffect(() => onReady(phase === "listening" || phase === "heard"), [phase, onReady]);

  const start = async () => {
    setPhase("asking");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { noiseSuppression: true, autoGainControl: true, echoCancellation: true },
      });
      const ctx = new AudioContext();
      const analyser = ctx.createAnalyser();
      ctx.createMediaStreamSource(stream).connect(analyser);
      let frame = 0;
      const tick = () => {
        const l = audioLevel(analyser);
        setLevel(l);
        if (l > HEARD_LEVEL) setPhase("heard");
        frame = requestAnimationFrame(tick);
      };
      tick();
      setPhase((p) => (p === "heard" ? p : "listening"));
      cleanup.current = () => {
        cancelAnimationFrame(frame);
        stream.getTracks().forEach((t) => t.stop());
        void ctx.close();
      };
    } catch (e) {
      setPhase(e instanceof DOMException && e.name === "NotFoundError" ? "missing" : "blocked");
    }
  };

  if (phase === "idle" || phase === "asking") {
    return (
      <button
        type="button"
        onClick={() => void start()}
        disabled={phase === "asking"}
        className="flex w-full items-center justify-center gap-2 rounded-[12px] border border-divider bg-surface px-4 py-3 font-semibold text-ink transition-colors hover:border-primary disabled:opacity-60"
      >
        <MicIcon size={18} className="text-primary" />
        {phase === "asking" ? "Allow the microphone in your browser…" : "Check your microphone"}
      </button>
    );
  }

  if (phase === "blocked" || phase === "missing") {
    return (
      <p role="alert" className="flex items-start gap-2 rounded-[12px] border border-divider bg-surface px-4 py-3 text-sm text-ink">
        <AlertIcon size={18} className="mt-0.5 shrink-0 text-error" />
        {phase === "missing"
          ? "No microphone found. Connect one, then reload this page."
          : "Microphone blocked. Allow it from the icon in your address bar, then reload this page."}
      </p>
    );
  }

  const heard = phase === "heard";
  return (
    <div className="rounded-[12px] border border-divider bg-surface px-4 py-3" role="status">
      <p className="flex items-center gap-2 text-sm font-semibold text-ink">
        {heard ? <CheckIcon size={18} className="text-primary" /> : <MicIcon size={18} className="text-primary" />}
        {heard ? "We can hear you. You're ready." : "Say something to test your mic…"}
      </p>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-divider/60" aria-hidden>
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-75"
          style={{ width: `${Math.min(100, level * 140)}%` }}
        />
      </div>
    </div>
  );
}
