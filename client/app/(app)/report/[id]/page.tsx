"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { AnswerCard, DeliveryStats, ScoreBars } from "@/components/ReportParts";
import { SharePanel } from "@/components/SharePanel";
import { gatewayFetch, useRequireAuth } from "@/lib/supabase";
import { LEVEL_LABEL, humanize, type SessionDetail } from "@/lib/report";
import { CARD, PAGE, PRIMARY, SECONDARY, WIDE_CARD } from "@/lib/ui";

const POLL_MS = 5000; // while the interview is still being scored or its recording disguised
const SEEK_LEAD_S = 0.3; // start a little before the line so its first word isn't clipped

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const auth = useRequireAuth();
  const uid = auth?.user.id;
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [missing, setMissing] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [playingAt, setPlayingAt] = useState<number | null>(null);
  const [shareOpen, setShareOpen] = useState(false);
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (!uid) return;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      try {
        const data = await gatewayFetch<SessionDetail>(`/sessions/${id}`);
        setSession(data);
        const busy = data.status === "live" || data.status === "scoring" || data.recording_status === "processing";
        if (busy) timer = setTimeout(load, POLL_MS);
      } catch {
        setMissing(true);
      }
    };
    void load();
    return () => clearTimeout(timer);
  }, [uid, id]);

  const hasRecording = session?.has_recording;
  useEffect(() => {
    if (!uid || !hasRecording) return;
    gatewayFetch<{ url: string }>(`/sessions/${id}/recording-url`).then((r) => setAudioUrl(r.url), () => {});
  }, [uid, id, hasRecording]);

  // MediaRecorder files carry no duration, so browsers report Infinity and seeking misbehaves until the
  // whole file is scanned: jump far past the end once to force that, then back to the start.
  const onLoadedMetadata = () => {
    const audio = audioRef.current;
    if (!audio || Number.isFinite(audio.duration)) return;
    audio.currentTime = 1e7;
    audio.addEventListener("durationchange", () => (audio.currentTime = 0), { once: true });
  };

  const base = session?.audio_started_at ?? null;
  const seek =
    audioUrl && base !== null
      ? (epoch: number) => {
          const audio = audioRef.current;
          if (!audio) return;
          audio.currentTime = Math.max(0, epoch - base - SEEK_LEAD_S);
          void audio.play();
        }
      : null;

  if (missing) {
    return (
      <main className={PAGE}>
        <div className={CARD}>
          <p className="text-ink">This interview doesn't exist or was deleted.</p>
          <a href="/history" className={`${SECONDARY} mt-4 inline-block`}>
            Back to history
          </a>
        </div>
      </main>
    );
  }
  if (!session) return <main className={PAGE} />;

  if (session.status === "live" || session.status === "scoring") {
    return (
      <main className={`${PAGE} flex items-center justify-center`}>
        <div className={`${CARD} text-center`} role="status">
          <p className="text-lg font-semibold text-ink">Scoring your interview…</p>
          <p className="mt-1 text-ink-secondary">This usually takes under a minute. This page updates by itself.</p>
        </div>
      </main>
    );
  }

  const report = session.report;
  if (session.status !== "scored" || !report || report.status !== "scored") {
    return (
      <main className={PAGE}>
        <div className={CARD}>
          <h1 className="text-xl font-bold text-ink">
            {session.status === "abandoned" ? "No answers were recorded" : "We couldn't score this interview"}
          </h1>
          <p className="mt-2 text-ink-secondary">Your credit was refunded, so you can try again.</p>
          <a href="/new" className={`${PRIMARY} mt-4 inline-block`}>
            Try again
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className={`${PAGE} pb-32`}>
      <title>{`${report.verdict} · ${report.overall_score}/100 · VoiceWire Interview`}</title>
      <div className="mx-auto w-full max-w-2xl space-y-6">
        <header className={WIDE_CARD}>
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-sm text-ink-secondary">
                {LEVEL_LABEL[session.seniority] ?? session.seniority} {session.role} ·{" "}
                {new Date(session.created_at).toLocaleDateString()}
              </p>
              <p className="mt-2 text-5xl font-bold text-ink tabular-nums">
                {report.overall_score}
                <span className="text-xl font-normal text-ink-secondary">/100</span>
              </p>
              <p className="mt-2 inline-block rounded-full border border-primary px-3 py-0.5 text-sm font-semibold text-primary">
                {report.verdict}
              </p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <button onClick={() => setShareOpen(true)} className={PRIMARY}>
                Share result
              </button>
              <a href={`/new?again=${session.id}`} className={SECONDARY}>
                Practice again
              </a>
            </div>
          </div>
          {report.top_strength && report.top_fix && (
            <p className="mt-4 text-ink">
              Your strongest area was <span className="font-semibold">{humanize(report.top_strength).toLowerCase()}</span>. Focus next on{" "}
              <span className="font-semibold">{humanize(report.top_fix).toLowerCase()}</span>.
            </p>
          )}
        </header>

        {report.dimensions && (
          <section className={WIDE_CARD}>
            <h2 className="mb-4 text-lg font-bold text-ink">Skills</h2>
            <ScoreBars dimensions={report.dimensions} rubric={report.rubric} strongest={report.top_strength} weakest={report.top_fix} />
          </section>
        )}

        <section className={WIDE_CARD}>
          <h2 className="mb-4 text-lg font-bold text-ink">How you spoke</h2>
          <DeliveryStats delivery={report.delivery} />
        </section>

        <section className="space-y-3">
          <h2 className="text-lg font-bold text-ink">Question by question</h2>
          {report.answers.map((a, i) => (
            <AnswerCard key={a.index} answer={a} number={i + 1} defaultOpen={i === 0} playingAt={playingAt} onSeek={seek} />
          ))}
        </section>

        <p className="text-center">
          <a href="/history" className="text-sm text-link hover:underline">
            All your interviews
          </a>
        </p>
      </div>

      <SharePanel
        open={shareOpen}
        onClose={() => setShareOpen(false)}
        sessionId={session.id}
        report={report}
        role={session.role}
        seniority={session.seniority}
        createdAt={session.created_at}
        suggestedName={session.suggested_name}
        initial={session.share}
      />

      {session.recording_status === "processing" && (
        <div className="fixed inset-x-0 bottom-0 border-t border-divider bg-surface/95 px-4 py-3 backdrop-blur">
          <p className="mx-auto max-w-2xl text-sm text-ink-secondary" role="status">
            Disguising your voice for the replay…
          </p>
        </div>
      )}
      {audioUrl && (
        <div className="fixed inset-x-0 bottom-0 border-t border-divider bg-surface/95 px-4 py-3 backdrop-blur">
          <div className="mx-auto flex max-w-2xl items-center gap-3">
            <span className="shrink-0 text-sm font-semibold text-ink">Replay</span>
            {session.recording_status === "ready" && (
              <span
                className="shrink-0 rounded-full border border-divider px-2 py-0.5 text-xs text-ink-secondary"
                title="Your side of the call is pitch- and formant-shifted before it's stored. Your original audio isn't kept."
              >
                Voice disguised
              </span>
            )}
            <audio
              ref={audioRef}
              src={audioUrl}
              controls
              preload="auto"
              onLoadedMetadata={onLoadedMetadata}
              onTimeUpdate={(e) => base !== null && !e.currentTarget.paused && setPlayingAt(base + e.currentTarget.currentTime)}
              onPause={() => setPlayingAt(null)}
              className="w-full"
            />
          </div>
        </div>
      )}
    </main>
  );
}
