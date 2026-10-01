"use client";

import { useEffect, useState } from "react";
import { Progress } from "@/components/Progress";
import { LEVEL_LABEL } from "@/lib/report";
import { gatewayFetch, useRequireAuth, type InterviewSession } from "@/lib/supabase";
import { PAGE, PRIMARY, WIDE_CARD } from "@/lib/ui";

const POLL_MS = 5000; // while a report is still being scored

const STATUS: Record<InterviewSession["status"], string> = {
  created: "Not started",
  live: "In progress",
  scoring: "Scoring…",
  scored: "",
  failed: "Couldn't score · refunded",
  abandoned: "No answers · refunded",
};

export default function History() {
  const auth = useRequireAuth();
  const [rows, setRows] = useState<InterviewSession[] | null>(null);

  const uid = auth?.user.id; // not the session object: it changes on every token refresh
  useEffect(() => {
    if (!uid) return;
    let timer: ReturnType<typeof setTimeout>;
    const load = async () => {
      const data = await gatewayFetch<InterviewSession[]>("/sessions").catch(() => [] as InterviewSession[]);
      setRows(data);
      if (data.some((r) => r.status === "scoring" || r.status === "live")) timer = setTimeout(load, POLL_MS);
    };
    void load();
    return () => clearTimeout(timer);
  }, [uid]);

  const remove = async (row: InterviewSession) => {
    if (!window.confirm(`Delete the ${row.role} interview from ${new Date(row.created_at).toLocaleDateString()}?`)) return;
    try {
      await gatewayFetch(`/sessions/${row.id}`, { method: "DELETE" });
      setRows((list) => list?.filter((r) => r.id !== row.id) ?? null);
    } catch {
      window.alert("Couldn't delete it. Try again.");
    }
  };

  return (
    <main className={PAGE}>
      <title>Your interviews · VoiceWire Interview</title>
      <div className={WIDE_CARD}>
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-bold text-ink">Your interviews</h1>
          <a href="/new" className={PRIMARY}>
            New interview
          </a>
        </div>
        {rows?.length === 0 && (
          <div className="mt-8 rounded-[12px] bg-bg px-6 py-10 text-center">
            <p className="font-semibold text-ink">No interviews yet</p>
            <p className="mx-auto mt-1 max-w-sm text-sm text-ink-secondary">
              Your practice interviews and their reports will appear here. The first one takes about 20 minutes.
            </p>
            <a href="/new" className={`${PRIMARY} mt-5 inline-block`}>
              Start your first mock
            </a>
          </div>
        )}
        {rows && <Progress rows={rows} />}
        <ul className="mt-6 divide-y divide-divider">
          {rows?.map((r) => (
            <li key={r.id} className="flex items-center gap-2 py-2">
              <a
                href={`/report/${r.id}`}
                className="flex flex-1 items-center justify-between gap-4 rounded-[8px] px-2 py-1 hover:bg-divider/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
              >
                <span>
                  <span className="block font-semibold text-ink">
                    {LEVEL_LABEL[r.seniority] ?? r.seniority} · {r.role}
                  </span>
                  <span className="block text-sm text-ink-secondary">{new Date(r.created_at).toLocaleString()}</span>
                </span>
                {r.status === "scored" ? (
                  <span className="text-right">
                    <span className="block text-xl font-bold text-ink tabular-nums">{r.overall_score}/100</span>
                    <span className="text-sm text-ink-secondary">{r.verdict}</span>
                  </span>
                ) : (
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                      r.status === "scoring" || r.status === "live" ? "bg-primary/10 text-primary" : "bg-divider/50 text-ink-secondary"
                    }`}
                  >
                    {STATUS[r.status]}
                  </span>
                )}
              </a>
              <button
                onClick={() => void remove(r)}
                aria-label={`Delete ${r.role} interview`}
                className="shrink-0 rounded-full px-3 py-1 text-sm text-ink-secondary hover:text-error focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
