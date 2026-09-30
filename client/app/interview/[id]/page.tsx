"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { Orb } from "@/components/Orb";
import { Captions } from "@/components/Captions";
import { CallControls } from "@/components/CallControls";
import { ErrorNotice } from "@/components/ErrorNotice";
import { HistoryDrawer } from "@/components/HistoryDrawer";
import { gatewayFetch, useRequireAuth, type InterviewSession } from "@/lib/supabase";
import { useVoiceSession } from "@/lib/useVoiceSession";
import { CARD, PAGE, PRIMARY } from "@/lib/ui";

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

  if (!row || !auth) return <main className={PAGE} />;

  if (saving) {
    return (
      <main className={`${PAGE} flex items-center justify-center`}>
        <p role="status" className="text-ink-secondary">
          Saving your interview…
        </p>
      </main>
    );
  }

  if (!started || (call.error && call.state === "disconnected")) {
    return (
      <main className={`${PAGE} flex flex-col items-center justify-center gap-6`}>
        {call.error ? (
          <ErrorNotice
            kind={call.error}
            onAction={() => window.location.assign(call.error === "dropped" ? "/history" : "/new")}
          />
        ) : (
          <div className={`${CARD} text-center`}>
            <h1 className="text-2xl font-bold text-ink">Ready when you are</h1>
            <p className="mt-2 text-ink-secondary">
              {row.seniority} {row.role} · about 20 minutes. Find a quiet spot. The interviewer speaks first, and you can
              interrupt anytime.
            </p>
            <button onClick={start} className={`${PRIMARY} mt-6`}>
              Start interview
            </button>
          </div>
        )}
      </main>
    );
  }

  const question = call.question;
  return (
    <main className="min-h-dvh flex flex-col items-center bg-bg px-4 font-sans motion-safe:animate-fade-in">
      <div className="flex-1 w-full flex flex-col items-center justify-center gap-6">
        {question && (
          <div className="max-w-md text-center">
            <p className="text-xs font-semibold text-ink-secondary tabular-nums">
              Question {question.index + 1} of {question.total}
            </p>
            <p className="mt-1 text-ink">{question.text}</p>
          </div>
        )}
        <Orb
          state={call.connecting ? "connecting" : call.state}
          size={240}
          interruptTick={call.interruptTick}
          getLevel={call.getLevel}
          getMicLevel={call.getMicLevel}
        />
        <p aria-live="polite" className="text-ink-secondary text-[0.9375rem] font-semibold">
          {call.connecting ? "Connecting…" : call.muted ? "Muted" : STATE_LABEL[call.state]}
        </p>
        <Captions turns={call.turns} state={call.state} hint={null} />
      </div>
      <CallControls
        muted={call.muted}
        micReady={!call.connecting && call.state !== "disconnected"}
        onToggleMute={call.toggleMute}
        onHistory={() => setHistoryOpen(true)}
        onEnd={call.endCall}
      />
      <HistoryDrawer open={historyOpen} onClose={() => setHistoryOpen(false)} turns={call.turns} />
    </main>
  );
}
