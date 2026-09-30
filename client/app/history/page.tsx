"use client";

import { useEffect, useState } from "react";
import { gatewayFetch, useRequireAuth, type InterviewSession } from "@/lib/supabase";
import { CARD, PAGE, PRIMARY } from "@/lib/ui";

const POLL_MS = 5000; // while a report is still being scored

const STATUS: Record<InterviewSession["status"], string> = {
  created: "Not started",
  live: "In progress",
  scoring: "Scoring…",
  scored: "",
  failed: "Couldn't score, credit refunded",
  abandoned: "No answers, credit refunded",
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

  return (
    <main className={PAGE}>
      <div className={CARD}>
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-bold text-ink">Your interviews</h1>
          <a href="/new" className={PRIMARY}>
            New interview
          </a>
        </div>
        {rows?.length === 0 && <p className="mt-6 text-ink-secondary">No interviews yet.</p>}
        <ul className="mt-6 divide-y divide-divider">
          {rows?.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-4 py-3">
              <div>
                <p className="font-semibold text-ink capitalize">
                  {r.seniority} {r.role}
                </p>
                <p className="text-sm text-ink-secondary">{new Date(r.created_at).toLocaleString()}</p>
              </div>
              {r.status === "scored" ? (
                <p className="text-right">
                  <span className="block text-xl font-bold text-ink tabular-nums">{r.overall_score}/100</span>
                  <span className="text-sm text-ink-secondary">{r.verdict}</span>
                </p>
              ) : (
                <p className="text-sm text-ink-secondary text-right">{STATUS[r.status]}</p>
              )}
            </li>
          ))}
        </ul>
      </div>
    </main>
  );
}
