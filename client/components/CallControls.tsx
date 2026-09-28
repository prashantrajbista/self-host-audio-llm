import type { ReactNode } from "react";

const BUTTON =
  "size-14 rounded-full flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary";
const NEUTRAL = "bg-surface text-ink shadow-ambient hover:bg-divider/40";

export function CallControls({
  muted,
  micReady,
  onToggleMute,
  onHistory,
  onEnd,
}: {
  muted: boolean;
  micReady: boolean;
  onToggleMute: () => void;
  onHistory: () => void;
  onEnd: () => void;
}) {
  return (
    <div className="w-full flex justify-center gap-6 pt-4 pb-[max(2rem,env(safe-area-inset-bottom))]">
      <button
        onClick={onToggleMute}
        disabled={!micReady}
        aria-label={muted ? "Unmute microphone" : "Mute microphone"}
        aria-pressed={muted}
        className={`${BUTTON} ${muted ? "bg-ink text-white" : NEUTRAL}`}
      >
        <Icon>
          <rect x="9" y="2" width="6" height="12" rx="3" />
          <path d="M5 10a7 7 0 0 0 14 0M12 17v4M8 21h8" />
          {muted && <path d="M3 3l18 18" />}
        </Icon>
      </button>
      <button onClick={onHistory} aria-label="Conversation history" className={`${BUTTON} ${NEUTRAL}`}>
        <Icon>
          <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" />
        </Icon>
      </button>
      <button onClick={onEnd} aria-label="End call" className={`${BUTTON} bg-error text-white hover:brightness-90`}>
        <Icon>
          <path d="M6 6l12 12M18 6L6 18" />
        </Icon>
      </button>
    </div>
  );
}

export function Icon({ children }: { children: ReactNode }) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}
