"use client";

import { Fragment, useState } from "react";
import { FILLER_RE, SOURCE_LABEL, deliveryMetrics, humanize, type Answer, type Delivery, type Verdict } from "@/lib/report";

// Status is never colour alone: always an icon + a word.
function StatusTag({ verdict }: { verdict: Verdict }) {
  return verdict === "good" ? (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary">
      <span aria-hidden>✓</span> On track
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-error">
      <span aria-hidden>!</span> Work on this
    </span>
  );
}

// One series, magnitude on a 1-5 scale: thin horizontal bars in one hue, value labels in ink.
export function ScoreBars({
  dimensions,
  rubric,
  strongest,
  weakest,
}: {
  dimensions: Record<string, number>;
  rubric?: { name: string; description: string }[];
  strongest?: string;
  weakest?: string;
}) {
  const names = rubric?.map((r) => r.name) ?? Object.keys(dimensions);
  return (
    <ul className="space-y-4">
      {names.map((name) => {
        const value = dimensions[name] ?? 0;
        const description = rubric?.find((r) => r.name === name)?.description;
        return (
          <li key={name}>
            <div className="flex items-baseline justify-between gap-3">
              <span className="font-semibold text-ink">
                {humanize(name)}
                {name === strongest && <span className="ml-2 text-xs font-semibold text-primary">✓ Strongest</span>}
                {name === weakest && <span className="ml-2 text-xs font-semibold text-error">! Focus here</span>}
              </span>
              <span className="text-sm text-ink tabular-nums">{value.toFixed(1)} / 5</span>
            </div>
            <div
              className="mt-1 h-2 w-full rounded-full bg-divider/60"
              role="img"
              aria-label={`${humanize(name)}: ${value.toFixed(1)} out of 5`}
              title={`${humanize(name)}: ${value.toFixed(1)} / 5`}
            >
              <div className="h-2 rounded-full bg-primary" style={{ width: `${(value / 5) * 100}%` }} />
            </div>
            {description && <p className="mt-1 text-xs text-ink-secondary">{description}</p>}
          </li>
        );
      })}
    </ul>
  );
}

export function DeliveryStats({ delivery }: { delivery: Delivery }) {
  return (
    <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {deliveryMetrics(delivery).map((m) => (
        <li key={m.label} className="rounded-[8px] border border-divider p-3">
          <p className="text-xs text-ink-secondary">{m.label}</p>
          <p className="mt-0.5 text-xl font-bold text-ink tabular-nums">{m.value}</p>
          {m.verdict && <StatusTag verdict={m.verdict} />}
          <p className="mt-1 text-xs text-ink-secondary">{m.hint}</p>
        </li>
      ))}
    </ul>
  );
}

function withFillers(text: string) {
  const parts = text.split(FILLER_RE);
  const found = text.match(FILLER_RE) ?? [];
  return parts.map((part, i) => (
    <Fragment key={i}>
      {part}
      {found[i] && (
        <mark title="Filler word" className="rounded bg-error/15 px-0.5 text-ink">
          {found[i]}
        </mark>
      )}
    </Fragment>
  ));
}

export function AnswerCard({
  answer,
  number,
  defaultOpen,
  playingAt,
  onSeek,
}: {
  answer: Answer;
  number: number;
  defaultOpen: boolean;
  playingAt: number | null; // epoch seconds the replay is at, if playing
  onSeek: ((epoch: number) => void) | null; // null: no recording
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [showImproved, setShowImproved] = useState(false);
  const bullets = (items?: string[]) => (
    <ul className="list-disc pl-5 space-y-1 text-sm text-ink">
      {items?.map((s, i) => <li key={i}>{s}</li>)}
    </ul>
  );

  return (
    <section className="rounded-[12px] border border-divider bg-surface">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-start justify-between gap-4 p-4 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary rounded-[12px]"
      >
        <span>
          <span className="block text-xs font-semibold text-ink-secondary">
            Question {number} · {SOURCE_LABEL[answer.source]}
          </span>
          <span className="mt-1 block font-semibold text-ink">{answer.question}</span>
        </span>
        <span className="shrink-0 text-lg font-bold text-ink tabular-nums">
          {answer.scored ? `${answer.score}` : "—"}
          <span className="text-xs font-normal text-ink-secondary">{answer.scored ? "/100" : ""}</span>
        </span>
      </button>

      {open && (
        <div className="space-y-4 border-t border-divider p-4">
          {!answer.scored && <p className="text-sm text-ink-secondary">Couldn't score this answer.</p>}

          {answer.cv_ref && (
            <div className="rounded-[8px] bg-bg p-3 text-sm">
              <p className="text-ink">
                <span className="font-semibold">Your CV says:</span> {answer.cv_ref}
              </p>
              {answer.cv_alignment && (
                <p className="mt-1 text-ink">
                  <span className="font-semibold">Your answer showed:</span> {answer.cv_alignment}
                </p>
              )}
            </div>
          )}

          <div>
            <p className="mb-2 text-sm font-semibold text-ink">
              Transcript {onSeek && <span className="font-normal text-ink-secondary">· click a line to play it</span>}
            </p>
            <ol className="space-y-1">
              {answer.turns.map((t, i) => {
                const playing = playingAt !== null && playingAt >= t.start && playingAt < t.end;
                const line = (
                  <>
                    <span className="font-semibold">{t.role === "user" ? "You" : "Interviewer"}: </span>
                    {t.role === "user" ? withFillers(t.text) : t.text}
                  </>
                );
                return (
                  <li key={i}>
                    {onSeek ? (
                      <button
                        onClick={() => onSeek(t.start)}
                        className={`w-full rounded-[6px] px-2 py-1 text-left text-sm transition-colors hover:bg-divider/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary ${
                          playing ? "bg-primary/10" : ""
                        } ${t.role === "user" ? "text-ink" : "text-ink-secondary"}`}
                      >
                        {line}
                      </button>
                    ) : (
                      <p className={`px-2 py-1 text-sm ${t.role === "user" ? "text-ink" : "text-ink-secondary"}`}>{line}</p>
                    )}
                  </li>
                );
              })}
            </ol>
          </div>

          {answer.scored && (
            <>
              {answer.scores && (
                <p className="flex flex-wrap gap-2 text-xs text-ink-secondary">
                  {Object.entries(answer.scores).map(([k, v]) => (
                    <span key={k} className="rounded-full border border-divider px-2 py-0.5 tabular-nums">
                      {humanize(k)} {v}/5
                    </span>
                  ))}
                </p>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="mb-1 text-sm font-semibold text-ink">What worked</p>
                  {bullets(answer.strengths)}
                </div>
                <div>
                  <p className="mb-1 text-sm font-semibold text-ink">What to improve</p>
                  {bullets(answer.improvements)}
                </div>
              </div>
              {answer.improved_answer && (
                <div>
                  <button
                    onClick={() => setShowImproved((s) => !s)}
                    aria-expanded={showImproved}
                    className="text-sm font-semibold text-link hover:underline"
                  >
                    {showImproved ? "Hide" : "Show"} a stronger version of your answer
                  </button>
                  {showImproved && <p className="mt-2 rounded-[8px] bg-bg p-3 text-sm text-ink">{answer.improved_answer}</p>}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
