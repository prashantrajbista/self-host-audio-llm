"use client";

import { useEffect, useState } from "react";
import { gatewayFetch, supabase, useRequireAuth, type Cv, type Profile } from "@/lib/supabase";
import { CARD, INPUT, LABEL, PAGE, PRIMARY, SECONDARY } from "@/lib/ui";

// Level of the job applied for (sets the bar for questions and grading), not the candidate's experience.
const LEVELS = [
  { id: "junior", label: "Entry level", examples: "Junior, Associate, Trainee" },
  { id: "mid", label: "Mid level", examples: "Accountant, Analyst, Engineer" },
  { id: "senior", label: "Senior", examples: "Senior, Lead, Manager" },
];

// best guess from the CV's years of experience; people often apply a level up, so it's only a default
function suggestedLevel(years: number | undefined): string | null {
  if (years === undefined || years === null) return null;
  return years <= 2 ? "junior" : years <= 6 ? "mid" : "senior";
}
const TYPES = [
  { id: "mixed", label: "Behavioral + HR" },
  { id: "behavioral", label: "Behavioral only" },
  { id: "hr", label: "HR screen only" },
];

export default function NewInterview() {
  const session = useRequireAuth();
  const [packs, setPacks] = useState<{ id: string; name: string }[]>([]);
  const [credits, setCredits] = useState<Profile | null>(null);
  const [cvs, setCvs] = useState<Cv[]>([]);
  const [packId, setPackId] = useState("");
  const [role, setRole] = useState("Software Engineer");
  const [seniority, setSeniority] = useState<string>("mid");
  const [type, setType] = useState("mixed");
  const [cvId, setCvId] = useState<string | null>(null);
  const [jd, setJd] = useState("");
  const [consent, setConsent] = useState(false);
  const [status, setStatus] = useState<string | null>(null); // progress line while working
  const [error, setError] = useState<string | null>(null);

  const uid = session?.user.id; // not the session object: it changes on every token refresh
  useEffect(() => {
    if (!uid) return;
    gatewayFetch<{ id: string; name: string }[]>("/packs")
      .then((p) => {
        setPacks(p);
        setPackId((cur) => cur || p[0]?.id || "");
      })
      .catch(() => setError("Can't reach the interview server. Is the gateway running?"));
    gatewayFetch<Profile>("/me").then(setCredits, () => {});
    gatewayFetch<Cv[]>("/cvs").then((list) => {
      setCvs(list);
      if (list[0]) setCvId(list[0].id);
    }, () => {});
  }, [uid]);

  // pre-select the level from the chosen CV (the user can still change it)
  const selectedYears = cvs.find((c) => c.id === cvId)?.cv_profile?.years_experience;
  useEffect(() => {
    const level = suggestedLevel(selectedYears);
    if (level) setSeniority(level);
  }, [cvId, selectedYears]);

  const run = async (label: string, work: () => Promise<void>) => {
    setStatus(label);
    setError(null);
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setStatus(null);
    }
  };

  const uploadFile = (file: File | undefined) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    void run("Reading your CV… this takes a few seconds", async () => {
      const cv = await gatewayFetch<Cv>("/cv", { method: "POST", body: form });
      setCvs((list) => [cv, ...list]);
      setCvId(cv.id);
    });
  };

  const deleteCv = (id: string) =>
    run("Deleting…", async () => {
      await gatewayFetch(`/cv/${id}`, { method: "DELETE" });
      setCvs((list) => list.filter((c) => c.id !== id));
      setCvId((cur) => (cur === id ? (cvs.find((c) => c.id !== id)?.id ?? null) : cur));
    });

  const start = (e: React.FormEvent) => {
    e.preventDefault();
    void run("Creating your interview…", async () => {
      const { id } = await gatewayFetch<{ id: string }>("/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          pack_id: packId,
          role,
          seniority,
          interview_type: type,
          cv_id: cvId,
          jd_text: jd || null,
        }),
      });
      setStatus("Preparing questions from your CV…");
      await gatewayFetch(`/sessions/${id}/prepare`, { method: "POST" });
      window.location.assign(`/interview/${id}`);
    });
  };

  if (!session) return <main className={PAGE} />;
  const selected = cvs.find((c) => c.id === cvId);
  const suggested = suggestedLevel(selected?.cv_profile?.years_experience);

  return (
    <main className={PAGE}>
      <form onSubmit={start} className={`${CARD} space-y-5`}>
        <div className="flex items-baseline justify-between gap-4">
          <h1 className="text-2xl font-bold text-ink">New mock interview</h1>
          <span className="flex gap-4 text-sm">
            <a href="/history" className="text-link hover:underline">
              History
            </a>
            <button
              type="button"
              onClick={() => void supabase.auth.signOut().then(() => window.location.assign("/"))}
              className="text-ink-secondary hover:text-ink"
            >
              Sign out
            </button>
          </span>
        </div>
        {credits && (
          <p className="text-sm text-ink-secondary">
            {credits.has_pass ? "Unlimited mocks active." : `${credits.credits} mock${credits.credits === 1 ? "" : "s"} left.`}
          </p>
        )}

        {packs.length > 1 && (
          <div>
            <label htmlFor="pack" className={LABEL}>
              Interview
            </label>
            <select id="pack" value={packId} onChange={(e) => setPackId(e.target.value)} className={INPUT}>
              {packs.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label htmlFor="role" className={LABEL}>
            Role you're interviewing for
          </label>
          <input id="role" required maxLength={80} value={role} onChange={(e) => setRole(e.target.value)} className={INPUT} />
        </div>

        <fieldset>
          <legend className={LABEL}>Level of the job you're applying for</legend>
          <div className="grid grid-cols-3 gap-2">
            {LEVELS.map((l) => (
              <label
                key={l.id}
                className="cursor-pointer rounded-[8px] border border-divider bg-surface px-3 py-2 text-center has-[:checked]:border-primary has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-primary"
              >
                <input type="radio" name="seniority" value={l.id} checked={seniority === l.id} onChange={() => setSeniority(l.id)} className="sr-only" />
                <span className="block text-sm font-semibold text-ink">{l.label}</span>
                <span className="block text-xs text-ink-secondary">{l.examples}</span>
              </label>
            ))}
          </div>
          {suggested && seniority === suggested && (
            <p className="mt-1 text-xs text-ink-secondary">Suggested from your CV. Change it if you're applying for a different level.</p>
          )}
        </fieldset>

        <div>
          <label htmlFor="type" className={LABEL}>
            Questions
          </label>
          <select id="type" value={type} onChange={(e) => setType(e.target.value)} className={INPUT}>
            {TYPES.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <fieldset>
          <legend className={LABEL}>Your CV (the interviewer asks about your experience)</legend>
          <div className="space-y-2">
            {cvs.map((cv) => (
              <div key={cv.id} className="flex items-center justify-between gap-2">
                <label className="flex items-center gap-2 text-ink">
                  <input type="radio" name="cv" checked={cvId === cv.id} onChange={() => setCvId(cv.id)} />
                  {cv.file_name}
                </label>
                <button type="button" onClick={() => void deleteCv(cv.id)} className="text-sm text-ink-secondary hover:text-error">
                  Delete
                </button>
              </div>
            ))}
            {cvs.length === 0 && <p className="text-sm text-ink-secondary">Upload your CV to start.</p>}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <label className={`${SECONDARY} cursor-pointer`}>
              Upload PDF, DOCX or TXT
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                className="sr-only"
                onChange={(e) => uploadFile(e.target.files?.[0])}
                disabled={!!status}
              />
            </label>
          </div>
          {selected?.cv_profile && (
            <div className="mt-3 rounded-[8px] border border-divider p-3 text-sm">
              <p className="font-semibold text-ink">{selected.cv_profile.headline}</p>
              <ul className="mt-1 text-ink-secondary">
                {selected.cv_profile.roles?.slice(0, 4).map((r, i) => (
                  <li key={i}>
                    {r.title} · {r.company} {r.dates && `(${r.dates})`}
                  </li>
                ))}
              </ul>
              {!!selected.cv_profile.probe_points?.length && (
                <>
                  <p className="mt-2 font-semibold text-ink">The interviewer may ask about</p>
                  <ul className="list-disc pl-5 text-ink-secondary">
                    {selected.cv_profile.probe_points.slice(0, 5).map((p, i) => (
                      <li key={i}>{p.claim}</li>
                    ))}
                  </ul>
                </>
              )}
              <p className="mt-2 text-xs text-ink-secondary">Looks wrong? Delete it and upload a text-based PDF or DOCX.</p>
            </div>
          )}
        </fieldset>

        <div>
          <label htmlFor="jd" className={LABEL}>
            Job description (optional)
          </label>
          <textarea
            id="jd"
            rows={4}
            maxLength={8000}
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            className={INPUT}
            placeholder="Paste the job post to get questions about gaps between it and your CV"
          />
        </div>

        <label className="flex items-start gap-2 text-sm text-ink">
          <input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-1" />
          This mock is recorded and transcribed so you can replay it and get feedback. Recordings are private to you.
        </label>

        {error && (
          <p role="alert" className="text-sm text-error">
            {error}
          </p>
        )}
        <button type="submit" disabled={!!status || !packId || !cvId || !consent} className={`${PRIMARY} w-full`}>
          {status ?? "Start interview"}
        </button>
      </form>
    </main>
  );
}
