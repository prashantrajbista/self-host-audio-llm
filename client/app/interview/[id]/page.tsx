"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Orb } from "@/components/Orb";
import { Captions } from "@/components/Captions";
import { CallControls } from "@/components/CallControls";
import { ErrorNotice } from "@/components/ErrorNotice";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import { ClockIcon, HeadphonesIcon, WaveIcon } from "@/components/Icons";
import { MicCheck } from "@/components/MicCheck";
import { LEVEL_LABEL } from "@/lib/report";
import { gatewayFetch, useRequireAuth, type InterviewSession } from "@/lib/supabase";
import { useVoiceSession } from "@/lib/useVoiceSession";
import { PRIMARY, STANDALONE } from "@/lib/ui";

const STATE_LABEL = {
  idle: "Your turn",
  listening: "Listening…",
  thinking: "…",
  speaking: "Interviewer speaking",
  disconnected: "",
};

export default function InterviewCall() {
  const { id } = useParams<{ id: string }>();
  const auth = useRequireAuth();
  const [row, setRow] = useState<InterviewSession | null>(null);
  const [started, setStarted] = useState(false);
  const [saving, setSaving] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [micReady, setMicReady] = useState(false);
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [elapsed, setElapsed] = useState(0); // seconds since the first question
  const begunRef = useRef(false); // a question was asked: a refused or failed connect has nothing to save

  // Upload the call recording (stored privately by the gateway), then open the report (it waits for scoring).
  const onRecording = useCallback(
    (audio: Blob) => {
      if (!begunRef.current) return;
      setSaving(true);
      const form = new FormData();
      form.append("file", audio, `recording.${audio.type.includes("mp4") ? "m4a" : "webm"}`);
      void gatewayFetch(`/sessions/${id}/recording`, { method: "POST", body: form })
        .catch(() => {}) // the interview is still scored without a recording
        .finally(() => window.location.assign(`/report/${id}`));
    },
    [id],
  );

  const call = useVoiceSession({ onRecording });
  if (call.question) begunRef.current = true;

  const hasQuestion = !!call.question;
  useEffect(() => {
    if (!hasQuestion) return;
    const t0 = Date.now();
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(timer);
  }, [hasQuestion]);

  // Keyed on the user id, not the auth session object: Supabase hands out a new session object on every
  // token refresh (including when the tab regains focus). Re-checking then saw status "live" and
  // redirected away mid-interview, which closed the call.
  const uid = auth?.user.id;
  useEffect(() => {
    if (!uid) return;
    gatewayFetch<InterviewSession>(`/sessions/${id}`).then(
      (data) => (data.status === "created" ? setRow(data) : window.location.replace("/history")),
      () => window.location.replace("/history"),
    );
  }, [uid, id]);

  const start = () => {
    if (!auth) return;
    setStarted(true);
    call.connect({ interview: { session_id: id, token: auth.access_token } });
  };

  if (!row || !auth) return <main className={STANDALONE} />;

  if (saving) {
    return (
      <main className={`${STANDALONE} flex items-center justify-center px-4`}>
        <p role="status" className="flex items-center gap-2 text-ink-secondary">
          <span className="size-3 animate-pulse rounded-full bg-primary" aria-hidden />
          Saving your interview and preparing your report…
        </p>
      </main>
    );
  }

  if (!started || (call.error && call.state === "disconnected")) {
    return (
      <main className={`${STANDALONE} flex flex-col items-center justify-center gap-6 px-4 py-10`}>
        <title>Interview · VoiceWire Interview</title>
        {call.error ? (
          <ErrorNotice
            kind={call.error}
            onAction={() =>
              window.location.assign(call.error === "dropped" ? "/history" : call.error === "no-credits" ? "/new?buy=1" : "/new")
            }
          />
        ) : (
          <div className="w-full max-w-md">
            <h1 className="text-[2.125rem] font-bold leading-tight text-ink text-balance">Ready for your interview?</h1>
            <p className="mt-2 text-ink-secondary">
              {LEVEL_LABEL[row.seniority] ?? row.seniority} {row.role}. About 20 minutes, 5 questions.
            </p>
            <ul className="mt-6 space-y-3 text-[0.9375rem] text-ink">
              <Tip icon={<HeadphonesIcon size={18} />}>
                Use headphones in a quiet room. Speakers can echo the interviewer back into your mic.
              </Tip>
              <Tip icon={<WaveIcon size={18} />}>The interviewer speaks first. You can interrupt at any time.</Tip>
              <Tip icon={<ClockIcon size={18} />}>Answer like a real interview. Say &ldquo;skip&rdquo; to move on to the next question.</Tip>
            </ul>
            <div className="mt-6">
              <MicCheck onReady={setMicReady} />
            </div>
            <button onClick={start} disabled={!micReady} className={`${PRIMARY} mt-4 w-full py-3`}>
              Start interview
            </button>
            {!micReady && <p className="mt-2 text-center text-sm text-ink-secondary">Check your microphone first.</p>}
          </div>
        )}
      </main>
    );
  }

  const question = call.question;
  const progress = question ? ((question.index + 1) / question.total) * 100 : 0;
  return (
    <main className={`${STANDALONE} flex flex-col items-center px-4 motion-safe:animate-fade-in`}>
      <title>Interview in progress · VoiceWire Interview</title>
      <div className="w-full max-w-md pt-6">
        <div className="flex items-center justify-between text-xs font-semibold text-ink-secondary tabular-nums">
          <span>{question ? `Question ${question.index + 1} of ${question.total}` : "Starting…"}</span>
          <span>
            {formatClock(elapsed)} <span className="font-normal">/ ~20:00</span>
          </span>
        </div>
        <div
          className="mt-2 h-1 overflow-hidden rounded-full bg-divider/60"
          role="progressbar"
          aria-label="Interview progress"
          aria-valuemin={0}
          aria-valuemax={question?.total ?? 5}
          aria-valuenow={question ? question.index + 1 : 0}
        >
          <div className="h-full rounded-full bg-primary transition-[width] duration-500" style={{ width: `${progress}%` }} />
        </div>
        {question && <p className="mt-4 text-center text-ink text-balance">{question.text}</p>}
      </div>
      <div className="flex w-full flex-1 flex-col items-center justify-center gap-6">
        <Orb
          state={call.connecting || call.reconnecting ? "connecting" : call.state}
          size={240}
          interruptTick={call.interruptTick}
          getLevel={call.getLevel}
          getMicLevel={call.getMicLevel}
        />
        <p aria-live="polite" className="text-[0.9375rem] font-semibold text-ink-secondary">
          {call.connecting ? "Connecting…" : call.reconnecting ? "Connection lost. Reconnecting…" : call.muted ? "Muted" : STATE_LABEL[call.state]}
        </p>
        <Captions turns={call.turns} state={call.state} hint={null} />
      </div>
      {confirmEnd && (
        <div role="alertdialog" aria-label="End the interview?" className="mb-2 w-full max-w-md rounded-[12px] border border-divider bg-surface p-4 shadow-ambient">
          <p className="font-semibold text-ink">End the interview now?</p>
          <p className="mt-1 text-sm text-ink-secondary">Your answers so far will still be scored.</p>
          <div className="mt-3 flex gap-2">
            <button onClick={call.endCall} className="rounded-full bg-error px-5 py-2 text-sm font-semibold text-white hover:brightness-95">
              End interview
            </button>
            <button onClick={() => setConfirmEnd(false)} className="rounded-full border border-divider px-5 py-2 text-sm text-ink hover:border-primary">
              Keep going
            </button>
          </div>
        </div>
      )}
      <CallControls
        muted={call.muted}
        micReady={!call.connecting && call.state !== "disconnected"}
        onToggleMute={call.toggleMute}
        onHistory={() => setHistoryOpen(true)}
        onEnd={() => setConfirmEnd(true)}
      />
      <HistoryDrawer open={historyOpen} onClose={() => setHistoryOpen(false)} turns={call.turns} />
    </main>
  );
}

function Tip({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-0.5 shrink-0 text-primary">{icon}</span>
      <span>{children}</span>
    </li>
  );
}

const formatClock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
