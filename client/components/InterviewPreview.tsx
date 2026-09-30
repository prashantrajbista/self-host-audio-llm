"use client";

// Landing-page preview of the live interview screen, built from the real Orb and Captions components
// (not a screenshot), playing a short scripted exchange on a loop. Purely illustrative: no mic, no socket.
import { useEffect, useRef, useState } from "react";
import { Captions } from "@/components/Captions";
import { Icon } from "@/components/CallControls";
import { Orb } from "@/components/Orb";
import type { Turn } from "@/lib/useVoiceSession";

const SCRIPT: { state: "speaking" | "listening"; turn: Turn }[] = [
  {
    state: "speaking",
    turn: { role: "assistant", text: "Your CV says you cut month-end close from ten days to six. What did you change first?" },
  },
  {
    state: "listening",
    turn: { role: "user", text: "I mapped every step of the close and found three reconciliations we could automate." },
  },
  {
    state: "speaking",
    turn: { role: "assistant", text: "Got it. How did you get the rest of the team to adopt the new process?" },
  },
  {
    state: "listening",
    turn: { role: "user", text: "I ran the first two closes alongside them and wrote a one-page checklist." },
  },
];
const STEP_MS = 5200;

export function InterviewPreview() {
  const [step, setStep] = useState(0);
  const t0 = useRef(0);

  useEffect(() => {
    t0.current = performance.now();
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return; // hold the first frame
    const timer = setInterval(() => setStep((s) => (s + 1) % SCRIPT.length), STEP_MS);
    return () => clearInterval(timer);
  }, []);

  const { state, turn } = SCRIPT[step];
  // stand-in for live audio: a speech-like wobble, larger while the interviewer talks
  const getLevel = () => {
    const t = (performance.now() - t0.current) / 1000;
    const wobble = 0.5 + 0.5 * Math.sin(t * 7.3) * Math.sin(t * 2.1 + 1);
    return state === "speaking" ? 0.25 + 0.45 * wobble : 0.1 + 0.25 * wobble;
  };

  return (
    <div
      className="overflow-hidden rounded-[20px] border border-divider bg-bg shadow-[0_24px_48px_-12px_rgba(0,0,0,0.18)]"
      role="img"
      aria-label="The interview screen: a glowing orb shows who is speaking, with live captions and the current question above."
    >
      <div className="flex items-center gap-1.5 border-b border-divider bg-surface px-4 py-3" aria-hidden>
        <span className="size-2.5 rounded-full bg-divider" />
        <span className="size-2.5 rounded-full bg-divider" />
        <span className="size-2.5 rounded-full bg-divider" />
      </div>
      <div className="flex flex-col items-center px-6 pb-8 pt-6" aria-hidden>
        <div className="w-full max-w-md">
          <div className="flex items-center justify-between text-xs font-semibold text-ink-secondary tabular-nums">
            <span>Question 2 of 5</span>
            <span>
              6:48 <span className="font-normal">/ ~20:00</span>
            </span>
          </div>
          <div className="mt-2 h-1 overflow-hidden rounded-full bg-divider/60">
            <div className="h-full w-2/5 rounded-full bg-primary" />
          </div>
          <p className="mt-4 text-center text-ink text-balance">Tell me about a project you&apos;re proud of.</p>
        </div>
        <div className="my-8">
          <Orb state={state} size={200} getLevel={getLevel} />
        </div>
        <p className="text-[0.9375rem] font-semibold text-ink-secondary">
          {state === "speaking" ? "Interviewer speaking" : "Listening…"}
        </p>
        <div className="mt-3 w-full max-w-md">
          <Captions turns={[turn]} state={state} hint={null} />
        </div>
        <div className="mt-6 flex gap-5 [&_svg]:size-5">
          <span className="flex size-11 items-center justify-center rounded-full bg-surface text-ink shadow-ambient">
            <Icon>
              <rect x="9" y="2" width="6" height="12" rx="3" />
              <path d="M5 10a7 7 0 0 0 14 0M12 17v4M8 21h8" />
            </Icon>
          </span>
          <span className="flex size-11 items-center justify-center rounded-full bg-surface text-ink shadow-ambient">
            <Icon>
              <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
            </Icon>
          </span>
          <span className="flex size-11 items-center justify-center rounded-full bg-error text-white">
            <Icon>
              <path d="M6 6l12 12M18 6L6 18" />
            </Icon>
          </span>
        </div>
      </div>
    </div>
  );
}
