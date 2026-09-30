"use client";

import { useEffect, useState } from "react";
import { LEVEL_LABEL } from "@/lib/report";
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
                  <span className="text-sm text-ink-secondary text-right">{STATUS[r.status]}</span>
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
