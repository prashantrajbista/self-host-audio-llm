"use client";

import { useEffect, useRef, useState } from "react";
import { BuyPanel } from "@/components/BuyPanel";
import { refreshCredits } from "@/components/AppHeader";
import { AlertIcon, CheckIcon } from "@/components/Icons";
import type { SessionDetail } from "@/lib/report";
import { RETENTION_DAYS } from "@/lib/site";
import { GatewayError, gatewayFetch, useRequireAuth, type Cv, type Profile } from "@/lib/supabase";
import { INPUT, LABEL, PAGE, PRIMARY, SECONDARY } from "@/lib/ui";

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
  const [buy, setBuy] = useState<{ open: boolean; reason?: string }>({ open: false });
  const [paidNotice, setPaidNotice] = useState<string | null>(null);
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
  const prefilled = useRef(false); // fields copied from an earlier interview: don't override its level

  const uid = session?.user.id; // not the session object: it changes on every token refresh
  useEffect(() => {
    if (!uid) return;
    const params = new URLSearchParams(window.location.search);
    gatewayFetch<{ id: string; name: string }[]>("/packs")
      .then((p) => {
        setPacks(p);
        setPackId((cur) => cur || p[0]?.id || "");
      })
      .catch(() => setError("Can't reach the interview server. Is the gateway running?"));
    // "Practice again" from a report: same role, level, type, CV and job post
    const again = params.get("again");
    if (again) {
      gatewayFetch<SessionDetail & { interview_type: string; cv_id: string | null; jd_text: string | null }>(`/sessions/${again}`).then(
        (prev) => {
          prefilled.current = true;
          setPackId(prev.pack_id);
          setRole(prev.role);
          setSeniority(prev.seniority);
          setType(prev.interview_type);
          setJd(prev.jd_text ?? "");
          if (prev.cv_id) setCvId(prev.cv_id);
        },
        () => {},
      );
    }
    // Back from Stripe: the webhook grants the purchase, usually within seconds; watch /me until it shows.
    let timer: ReturnType<typeof setTimeout>;
    const watchForPayment = async (before: Profile, tries: number) => {
      const now = await gatewayFetch<Profile>("/me").catch(() => before);
      setCredits(now);
      if (now.credits !== before.credits || now.has_pass !== before.has_pass) {
        setPaidNotice("Payment received. Your mocks are ready.");
        refreshCredits();
      } else if (tries > 0) {
        timer = setTimeout(() => void watchForPayment(before, tries - 1), 2000);
      } else {
        setPaidNotice("Payment received. Your mocks can take a minute to appear; refresh this page shortly.");
      }
    };
    gatewayFetch<Profile>("/me").then((p) => {
      setCredits(p);
      if (params.get("buy") && p.payments_enabled) setBuy({ open: true, reason: "You've used your mocks. Pick a plan to keep practising." });
      if (params.get("paid")) {
        setPaidNotice("Payment received. Updating your mocks…");
        timer = setTimeout(() => void watchForPayment(p, 10), 2000);
      }
    }, () => {});
    gatewayFetch<Cv[]>("/cvs").then((list) => {
      setCvs(list);
      setCvId((cur) => (cur && list.some((c) => c.id === cur) ? cur : (list[0]?.id ?? null)));
    }, () => {});
    return () => clearTimeout(timer);
  }, [uid]);

  // pre-select the level from the chosen CV (the user can still change it)
  const selectedYears = cvs.find((c) => c.id === cvId)?.cv_profile?.years_experience;
  useEffect(() => {
    const level = suggestedLevel(selectedYears);
    if (level && !prefilled.current) setSeniority(level);
  }, [cvId, selectedYears]);

  const run = async (label: string, work: () => Promise<void>) => {
    setStatus(label);
    setError(null);
    try {
      await work();
    } catch (e) {
      if (e instanceof GatewayError && e.status === 402) setBuy({ open: true, reason: e.message });
      else setError(e instanceof Error ? e.message : String(e));
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
      refreshCredits();
      window.location.assign(`/interview/${id}`);
    });
  };

  if (!session) return <main className={PAGE} />;
  const selected = cvs.find((c) => c.id === cvId);
  const suggested = suggestedLevel(selected?.cv_profile?.years_experience);
  const blocker = !cvId
    ? "Add your CV to continue."
    : !role.trim()
      ? "Enter the role you're interviewing for."
      : !consent
        ? "Tick the recording consent to start."
        : null;

  return (
    <main className={PAGE}>
      <title>New interview · VoiceWire Interview</title>
      <form onSubmit={start} className="mx-auto w-full max-w-2xl">
        <h1 className="text-[2.125rem] font-bold leading-tight text-ink text-balance">Set up your mock interview</h1>
        <p className="mt-2 text-ink-secondary">
          About 20 minutes, 5 questions, by voice. You get a scored report straight after.
        </p>
        {paidNotice && (
          <p role="status" className="mt-6 flex items-center gap-2 rounded-[12px] bg-primary/10 px-4 py-3 text-sm text-ink">
            <CheckIcon size={18} className="shrink-0 text-primary" />
            {paidNotice}
          </p>
        )}

        <ol className="mt-8 space-y-4">
          <Step n={1} title="Your CV" done={!!cvId}>
            <p className="text-sm text-ink-secondary">
              The interviewer asks about your real experience, so questions are built from your CV. Your name, contact
              details, and LinkedIn or GitHub links and IDs are removed before the AI reads it, and the original file is never stored.
            </p>
            {cvs.length > 0 && (
              <div className="mt-4 space-y-1" role="radiogroup" aria-label="Your CVs">
                {cvs.map((cv) => (
                  <div
                    key={cv.id}
                    className="flex items-center justify-between gap-3 rounded-[8px] px-3 py-2 has-[:checked]:bg-primary/10"
                  >
                    <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-3 text-ink">
                      <input type="radio" name="cv" checked={cvId === cv.id} onChange={() => setCvId(cv.id)} />
                      <span className="truncate">{cv.file_name}</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => void deleteCv(cv.id)}
                      aria-label={`Delete ${cv.file_name}`}
                      className="shrink-0 text-sm text-ink-secondary hover:text-error"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
            <label className={`${SECONDARY} mt-4 inline-flex cursor-pointer items-center gap-2 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-primary`}>
              {cvs.length ? "Upload another CV" : "Upload your CV"}
              <span className="text-ink-secondary">PDF, DOCX or TXT</span>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                className="sr-only"
                onChange={(e) => uploadFile(e.target.files?.[0])}
                disabled={!!status}
              />
            </label>
            {status?.startsWith("Reading") && (
              <p role="status" className="mt-3 flex items-center gap-2 text-sm text-ink-secondary">
                <span className="size-3 animate-pulse rounded-full bg-primary" aria-hidden />
                {status}
              </p>
            )}
            {selected?.cv_profile && (
              <div className="mt-4 rounded-[12px] bg-bg p-4 text-sm">
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
                    <p className="mt-3 font-semibold text-ink">The interviewer may ask about</p>
                    <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink-secondary">
                      {selected.cv_profile.probe_points.slice(0, 5).map((p, i) => (
                        <li key={i}>{p.claim}</li>
                      ))}
                    </ul>
                  </>
                )}
                <p className="mt-3 text-xs text-ink-secondary">Looks wrong? Delete it and upload a text-based PDF or DOCX.</p>
              </div>
            )}
            {selected?.anon_text && (
              <details className="mt-3 rounded-[12px] border border-divider p-4 text-sm">
                <summary className="cursor-pointer font-semibold text-ink">What the AI sees</summary>
                <p className="mt-2 text-xs text-ink-secondary">
                  Your CV after anonymization. This is all that's sent to the AI and all we keep.
                </p>
                <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap font-sans text-ink-secondary">
                  {selected.anon_text.split(/(\[[A-Z]+\])/).map((part, i) =>
                    i % 2 ? (
                      <mark key={i} className="rounded bg-primary/15 px-1 font-semibold text-primary">
                        {part}
                      </mark>
                    ) : (
                      part
                    ),
                  )}
                </pre>
              </details>
            )}
          </Step>

          <Step n={2} title="The job" done={!!role.trim()}>
            {packs.length > 1 && (
              <div className="mb-4">
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
            <label htmlFor="role" className={LABEL}>
              Role you&apos;re interviewing for
            </label>
            <input
              id="role"
              required
              maxLength={80}
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className={INPUT}
              placeholder="e.g. Accountant, Product Manager, Nurse"
            />
            <fieldset className="mt-5">
              <legend className={LABEL}>Level of the job</legend>
              <div className="grid grid-cols-3 gap-2">
                {LEVELS.map((l) => (
                  <label
                    key={l.id}
                    className="cursor-pointer rounded-[8px] border border-divider bg-surface px-3 py-2 text-center transition-colors hover:border-primary has-[:checked]:border-primary has-[:checked]:bg-primary/10 has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-primary"
                  >
                    <input type="radio" name="seniority" value={l.id} checked={seniority === l.id} onChange={() => setSeniority(l.id)} className="sr-only" />
                    <span className="block text-sm font-semibold text-ink">{l.label}</span>
                    <span className="block text-xs text-ink-secondary">{l.examples}</span>
                  </label>
                ))}
              </div>
              {suggested && seniority === suggested && (
                <p className="mt-2 text-xs text-ink-secondary">Suggested from your CV. Change it if you&apos;re applying for a different level.</p>
              )}
            </fieldset>
            <div className="mt-5">
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
          </Step>

          <Step n={3} title="Job post (optional)" done={!!jd.trim()}>
            <label htmlFor="jd" className="sr-only">
              Job description
            </label>
            <textarea
              id="jd"
              rows={4}
              maxLength={8000}
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              className={INPUT}
              placeholder="Paste the job post to get a question on the gap between it and your CV."
            />
          </Step>
        </ol>

        <div className="mt-6 space-y-4">
          <label className="flex items-start gap-3 text-sm text-ink">
            <input type="checkbox" required checked={consent} onChange={(e) => setConsent(e.target.checked)} className="mt-0.5 size-4 shrink-0" />
            <span>
              Record and transcribe this interview so I can replay it and get feedback. The replay is stored with my
              voice disguised, private to you and deleted after {RETENTION_DAYS} days. <a href="/privacy" className="text-link underline">Privacy policy</a>
            </span>
          </label>
          {error && (
            <p role="alert" className="flex items-start gap-2 text-sm text-error">
              <AlertIcon size={18} className="mt-0.5 shrink-0" />
              {error}
            </p>
          )}
          <button type="submit" disabled={!!status || !packId || !!blocker} className={`${PRIMARY} w-full py-3`}>
            {status && !status.startsWith("Reading") ? status : "Start interview"}
          </button>
          {blocker && !status && <p className="text-center text-sm text-ink-secondary">{blocker}</p>}
        </div>
      </form>
      <BuyPanel open={buy.open} onClose={() => setBuy({ open: false })} reason={buy.reason} />
    </main>
  );
}

function Step({ n, title, done, children }: { n: number; title: string; done: boolean; children: React.ReactNode }) {
  return (
    <li className="rounded-[12px] border border-divider bg-surface p-5 sm:p-6">
      <h2 className="flex items-center gap-3 text-[1.0625rem] font-semibold text-ink">
        <span
          className={`flex size-7 shrink-0 items-center justify-center rounded-full text-sm tabular-nums ${
            done ? "bg-primary text-white" : "border border-divider text-ink-secondary"
          }`}
          aria-hidden
        >
          {done ? <CheckIcon size={16} /> : n}
        </span>
        {title}
        {done && <span className="sr-only">(done)</span>}
      </h2>
      <div className="mt-4 sm:pl-10">{children}</div>
    </li>
  );
}
