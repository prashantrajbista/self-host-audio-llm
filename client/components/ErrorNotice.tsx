import type { ErrorKind } from "@/lib/useVoiceSession";

const COPY: Record<ErrorKind, { title: string; body: string; action: string }> = {
  mic: {
    title: "Microphone blocked",
    body: "Allow microphone access from the icon in your address bar, then try again.",
    action: "Try again",
  },
  "no-mic": {
    title: "No microphone found",
    body: "Connect a microphone and try again.",
    action: "Try again",
  },
  unreachable: {
    title: "Can't reach the voice server",
    body: "Make sure the gateway is running, then retry.",
    action: "Retry",
  },
  dropped: {
    title: "Connection lost",
    body: "The call dropped. Your conversation is still here.",
    action: "Reconnect",
  },
};

export function ErrorNotice({ kind, onAction }: { kind: ErrorKind; onAction: () => void }) {
  const { title, body, action } = COPY[kind];
  return (
    <div
      role="alert"
      className="w-full max-w-sm rounded-[12px] border border-divider bg-surface px-5 py-4 text-center shadow-ambient"
    >
      <p className="font-semibold text-ink">{title}</p>
      <p className="mt-1 text-sm text-ink-secondary">{body}</p>
      <button
        onClick={onAction}
        className="mt-3 rounded-full px-5 py-2 text-sm font-semibold bg-primary hover:bg-primary-hover text-white transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        {action}
      </button>
    </div>
  );
}
