"use client";

import { useState } from "react";
import { Orb } from "@/components/Orb";
import { Captions } from "@/components/Captions";
import { CallControls } from "@/components/CallControls";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import { useVoiceSession } from "@/lib/useVoiceSession";

const PROMPTS = ["Plan my day", "Explain something simply", "Practice a conversation"];

const STATE_LABEL = {
  connecting: "Connecting…",
  idle: "Go ahead, I'm listening",
  listening: "Listening…",
  thinking: "Thinking…",
  speaking: "Speaking · talk anytime to interrupt",
  disconnected: "",
};

export default function Home() {
  const { state, turns, connecting, error, interruptTick, muted, connect, endCall, toggleMute, getLevel } =
    useVoiceSession();
  const [hint, setHint] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const inCall = connecting || state !== "disconnected";

  const start = (prompt: string | null) => {
    setHint(prompt);
    connect();
  };

  const hangUp = () => {
    setHistoryOpen(false);
    endCall();
  };

  if (!inCall) {
    return (
      <main className="min-h-dvh flex flex-col items-center justify-center gap-8 bg-bg px-4 font-sans motion-safe:animate-fade-in">
        <Orb state="disconnected" size={200} />
        <div className="text-center">
          <h1 className="text-[2.125rem] font-bold leading-tight text-ink">Talk to your assistant</h1>
          <p className="mt-2 text-ink-secondary">Just speak naturally — interrupt anytime.</p>
        </div>
        <button
          onClick={() => start(null)}
          className="rounded-full px-7 py-3 text-[0.9375rem] font-semibold bg-primary hover:bg-primary-hover text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          Start talking
        </button>
        <div className="flex flex-wrap justify-center gap-2 max-w-md">
          {PROMPTS.map((prompt) => (
            <button
              key={prompt}
              onClick={() => start(prompt)}
              className="rounded-full border border-divider bg-surface px-4 py-2 text-sm text-ink hover:border-primary hover:text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
              {prompt}
            </button>
          ))}
        </div>
        <p className="text-ink-secondary text-xs">Uses your microphone — nothing is recorded or stored.</p>
        {error && <p className="text-error text-sm">{error}</p>}
      </main>
    );
  }

  const label = connecting ? STATE_LABEL.connecting : muted ? "Muted" : STATE_LABEL[state];

  return (
    <main className="min-h-dvh flex flex-col items-center bg-bg px-4 font-sans motion-safe:animate-fade-in">
      <div className="flex-1 w-full flex flex-col items-center justify-center gap-6">
        <Orb
          state={connecting ? "connecting" : state}
          size={280}
          interruptTick={interruptTick}
          getLevel={getLevel}
        />
        <p aria-live="polite" className="text-ink-secondary text-[0.9375rem] font-semibold">
          {label}
        </p>
        <Captions turns={turns} state={state} hint={hint} />
        {error && <p className="text-error text-sm">{error}</p>}
      </div>
      <CallControls
        muted={muted}
        micReady={!connecting}
        onToggleMute={toggleMute}
        onHistory={() => setHistoryOpen(true)}
        onEnd={hangUp}
      />
      <HistoryDrawer open={historyOpen} onClose={() => setHistoryOpen(false)} turns={turns} />
    </main>
  );
}
