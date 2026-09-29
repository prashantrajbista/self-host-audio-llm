"use client";

import { useEffect, useState } from "react";
import { Orb } from "@/components/Orb";
import { Captions } from "@/components/Captions";
import { CallControls, Icon } from "@/components/CallControls";
import { ErrorNotice } from "@/components/ErrorNotice";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import { VoicePicker } from "@/components/VoicePicker";
import { feedbackEnabled, setFeedbackEnabled } from "@/lib/feedback";
import { useVoiceSession } from "@/lib/useVoiceSession";
import { DEFAULT_VOICE, loadVoice, saveVoice, type Voice } from "@/lib/voices";
import type { InterviewParams } from "@/lib/ws";

const LATENCY_KEY = "show-latency";

const PROMPTS = ["Plan my day", "Explain something simply", "Practice a conversation"];

const STATE_LABEL = {
  connecting: "Connecting…",
  idle: "Go ahead, I'm listening",
  listening: "Listening…",
  thinking: "Thinking… · tap to stop",
  speaking: "Speaking · tap or talk to interrupt",
  disconnected: "",
};

export default function Home() {
  const {
    state,
    turns,
    connecting,
    error,
    interruptTick,
    muted,
    latency,
    question,
    interviewId,
    connect,
    endCall,
    interrupt,
    toggleMute,
    getLevel,
    getMicLevel,
  } = useVoiceSession();
  const [hint, setHint] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [voice, setVoice] = useState<Voice>(DEFAULT_VOICE);
  const [showLatency, setShowLatency] = useState(false);
  // ?pack=tech_behavioral&role=...&seniority=junior|mid|senior&type=behavioral|hr|mixed runs a mock interview
  const [interview, setInterview] = useState<InterviewParams | undefined>(undefined);

  // read after mount: localStorage isn't available during server render
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const pack = params.get("pack");
    if (pack) {
      setInterview({
        pack,
        role: params.get("role") ?? undefined,
        seniority: params.get("seniority") ?? undefined,
        type: params.get("type") ?? undefined,
      });
    }
    setVoice(loadVoice());
    try {
      setShowLatency(localStorage.getItem(LATENCY_KEY) === "on");
    } catch {
      // storage blocked: badge stays hidden by default
    }
  }, []);
  // a dropped call stays in the call view (grey orb + Reconnect) so captions and history survive
  const inCall = connecting || state !== "disconnected" || error === "dropped";

  const start = (prompt: string | null) => {
    setHint(prompt);
    connect({ voice: voice.id, interview });
  };

  const hangUp = () => {
    setHistoryOpen(false);
    endCall();
  };

  const pickVoice = (v: Voice) => {
    setVoice(v);
    saveVoice(v);
  };

  const toggleLatency = () => {
    setShowLatency((on) => {
      try {
        localStorage.setItem(LATENCY_KEY, on ? "off" : "on");
      } catch {
        // storage blocked: the setting just won't persist
      }
      return !on;
    });
  };

  // Keyboard shortcuts. Re-registered each render so handlers see current state. Skipped while a
  // sheet is open (the dialog owns Esc/focus) and in text fields; Space/Enter on a focused button
  // are left to the button's native click so they don't fire twice.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.repeat || e.metaKey || e.ctrlKey || e.altKey) return;
      if (document.querySelector("dialog[open]")) return;
      const target = e.target as HTMLElement;
      if (target.closest("input, textarea, select, [contenteditable]")) return;
      const onButton = target.closest("button") !== null;
      const key = e.key.toLowerCase();

      if (!inCall) {
        if (key === "enter" && !onButton) {
          e.preventDefault();
          start(null);
        }
        return;
      }
      if (key === " " && !onButton) {
        e.preventDefault();
        toggleMute();
      } else if (key === "escape") hangUp();
      else if (key === "h") setHistoryOpen(true);
      else if (key === "d") toggleLatency();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  if (!inCall) {
    return (
      <main className="min-h-dvh flex flex-col items-center justify-center gap-8 bg-bg px-4 font-sans motion-safe:animate-fade-in">
        <FeedbackToggle />
        <Orb state={error ? "disconnected" : "idle"} size={200} palette={voice.palette} />
        <div className="flex flex-col items-center text-center">
          <h1 className="text-[2.125rem] font-bold leading-tight text-ink">
            {interview ? "Mock interview" : "Talk to your assistant"}
          </h1>
          <p className="mt-2 text-ink-secondary">
            {interviewId
              ? "Interview complete. Your feedback report is being prepared."
              : interview
                ? `${interview.seniority ?? "mid"} ${interview.role ?? "Software Engineer"} · the interviewer speaks first`
                : "Just speak naturally — interrupt anytime."}
          </p>
          <button
            onClick={() => setPickerOpen(true)}
            className="mt-4 inline-flex items-center gap-1 rounded-full border border-divider bg-surface pl-4 pr-3 py-1.5 text-sm text-ink hover:border-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            Voice: <span className="font-semibold">{voice.name}</span>
            <Icon>
              <path d="M8 10l4 4 4-4" />
            </Icon>
          </button>
        </div>
        {error ? (
          <ErrorNotice kind={error} onAction={() => start(hint)} />
        ) : (
          <button
            onClick={() => start(null)}
            className="rounded-full px-7 py-3 text-[0.9375rem] font-semibold bg-primary hover:bg-primary-hover text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            {interview ? "Start interview" : "Start talking"}
          </button>
        )}
        <div className="flex flex-wrap justify-center gap-2 max-w-md">
          {(interview ? [] : PROMPTS).map((prompt) => (
            <button
              key={prompt}
              onClick={() => start(prompt)}
              className="rounded-full border border-divider bg-surface px-4 py-2 text-sm text-ink hover:border-primary hover:text-primary transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
            >
              {prompt}
            </button>
          ))}
        </div>
        <p className="text-ink-secondary text-xs">
          {interview
            ? "Uses your microphone — your answers are transcribed and saved for your feedback report."
            : "Uses your microphone — nothing is recorded or stored."}
        </p>
        <VoicePicker open={pickerOpen} onClose={() => setPickerOpen(false)} selected={voice} onSelect={pickVoice} />
      </main>
    );
  }

  const dropped = error === "dropped";
  const label = dropped
    ? "Connection lost"
    : connecting
      ? STATE_LABEL.connecting
      : muted
        ? "Muted"
        : STATE_LABEL[state];
  const canInterrupt = state === "thinking" || state === "speaking";

  return (
    <main className="min-h-dvh flex flex-col items-center bg-bg px-4 font-sans motion-safe:animate-fade-in">
      <FeedbackToggle />
      {showLatency && (
        <p
          title="Time from end of your turn to first reply audio (excludes the silence wait before the turn ends and device playback delay)"
          className="fixed top-6 left-4 text-xs text-ink-secondary tabular-nums"
        >
          {latency ? `first audio ${Math.round(latency.last)} ms · avg ${Math.round(latency.avg)} ms` : "first audio —"}
        </p>
      )}
      <div className="flex-1 w-full flex flex-col items-center justify-center gap-6">
        {question && (
          <div className="max-w-md text-center">
            <p className="text-xs font-semibold text-ink-secondary tabular-nums">
              Question {question.index + 1} of {question.total}
            </p>
            <p className="mt-1 text-ink">{question.text}</p>
          </div>
        )}
        <button
          onClick={interrupt}
          disabled={!canInterrupt}
          aria-label="Stop reply"
          className="rounded-full disabled:cursor-default focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-primary"
        >
          <Orb
            state={connecting ? "connecting" : state}
            size={280}
            interruptTick={interruptTick}
            getLevel={getLevel}
            getMicLevel={getMicLevel}
            palette={voice.palette}
          />
        </button>
        <p aria-live="polite" className="text-ink-secondary text-[0.9375rem] font-semibold">
          {label}
        </p>
        <Captions turns={turns} state={state} hint={hint} />
        {dropped && <ErrorNotice kind="dropped" onAction={() => connect({ voice: voice.id, keepTurns: true })} />}
      </div>
      <CallControls
        muted={muted}
        micReady={!connecting && state !== "disconnected"}
        onToggleMute={toggleMute}
        onHistory={() => setHistoryOpen(true)}
        onEnd={hangUp}
      />
      <p className="hidden [@media(pointer:fine)]:block -mt-4 pb-4 text-xs text-ink-secondary">
        Space mute · H history · Esc end · D latency
      </p>
      <HistoryDrawer open={historyOpen} onClose={() => setHistoryOpen(false)} turns={turns} />
    </main>
  );
}

function FeedbackToggle() {
  const [on, setOn] = useState(true);
  // read after mount: localStorage isn't available during server render
  useEffect(() => setOn(feedbackEnabled()), []);

  const toggle = () => {
    setFeedbackEnabled(!on);
    setOn(!on);
  };

  return (
    <button
      onClick={toggle}
      aria-label="Sound and haptics"
      aria-pressed={on}
      className="fixed top-4 right-4 size-10 rounded-full flex items-center justify-center text-ink-secondary hover:bg-divider/40 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
    >
      <Icon>
        <path d="M11 5L6 9H2v6h4l5 4V5z" />
        {on ? <path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14" /> : <path d="M22 9l-6 6M16 9l6 6" />}
      </Icon>
    </button>
  );
}
