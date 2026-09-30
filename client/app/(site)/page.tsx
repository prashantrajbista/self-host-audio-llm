import { ArrowRightIcon, CheckIcon, LockIcon, PlusIcon } from "@/components/Icons";
import { HeroActions } from "@/components/AuthAware";
import { InterviewPreview } from "@/components/InterviewPreview";
import { ScaledCard } from "@/components/ScaledCard";
import type { PublicCard } from "@/lib/share";
import { BRAND, FREE_MOCKS, PLANS, RETENTION_DAYS } from "@/lib/site";
import { PRIMARY } from "@/lib/ui";

// Illustrative only (labelled as a sample on the page): what a shared result card looks like.
const SAMPLE: PublicCard = {
  brand: BRAND,
  score: 78,
  verdict: "Hire",
  date: "2026-09-30",
  name: "AK",
  role: "Accountant",
  level: "Mid level",
  skills: { structure: 3.9, specificity: 4.1, impact: 3.4, reflection: 3.6, relevance: 4.3 },
  delivery: { wpm: 138, fillers_per_min: 1.8, avg_answer_s: 94 },
  top_strength: "relevance",
  quote: null,
};

const STEPS = [
  { title: "Upload your CV", body: "Pick the role and level you're going for. Paste the job post if you have one." },
  { title: "Talk it through", body: "A live AI interviewer asks about your real experience, follows up, and lets you interrupt." },
  { title: "Read your report", body: "Scores per skill and per answer, how you spoke, and a stronger version of each answer." },
];

const LIVE_POINTS = [
  "Follow-up questions when an answer needs more detail",
  "Questions built from your own CV and the job you want",
  "Live captions, and you can interrupt at any time",
]

const REPORT_POINTS = [
  "An overall score and a hire / no-hire style verdict for the level you chose",
  "Skill scores: structure, specificity, impact, reflection, relevance",
  "How you spoke: pace, filler words, answer length, response time",
  "Every answer replayable, with what worked, what to fix, and a stronger version",
  "For questions about your CV: whether your answer backed up what your CV claims",
];

const FAQ = [
  {
    q: "What kind of interviews can I practise?",
    a: "Behavioral and HR screening interviews for any role, from accountant to engineer. Questions come from a curated bank plus your own CV and the job post you paste, at the level you pick.",
  },
  {
    q: "Is it a real conversation?",
    a: "Yes. You talk out loud and the interviewer answers in real time, asks follow-ups when an answer is vague, and you can interrupt it, just like a person.",
  },
  {
    q: "How is my interview scored?",
    a: "Each answer is graded against a rubric by an AI model, calibrated to the level of the job. Delivery metrics like pace and filler words are measured from the recording. Treat it as practice feedback, not a hiring decision.",
  },
  {
    q: "Who can see my CV and recordings?",
    a: `Only you. Nothing is public unless you choose to share a result card, and that card never includes your transcript, recording or CV. Deleted items and recordings older than ${RETENTION_DAYS} days are permanently removed.`,
  },
  {
    q: "Do I need special equipment?",
    a: "A microphone and a quiet room. Headphones help, so your speakers don't echo the interviewer back into your mic.",
  },
  {
    q: "Can I get a refund?",
    a: `No. All purchases are final, so try your ${FREE_MOCKS} free mocks first. If an interview fails or ends before you answer anything, its credit goes back to your account automatically.`,
  },
];

export default function Landing() {
  return (
    <main>
      <section className="mx-auto grid max-w-5xl items-center gap-12 px-4 pb-20 pt-10 sm:pt-16 lg:grid-cols-[1.05fr_1fr]">
        <div>
          <h1 className="text-[2.75rem] font-bold leading-[1.05] tracking-[-0.02em] text-ink text-balance sm:text-6xl">
            Rehearse the interview before it counts.
          </h1>
          <p className="mt-5 max-w-lg text-lg text-ink-secondary">
            Talk to a live AI interviewer that asks about your real CV, pushes for specifics, and scores every answer. About
            20 minutes, entirely by voice.
          </p>
          <HeroActions />
          <p className="mt-4 flex items-center gap-2 text-sm text-ink-secondary">
            <LockIcon size={16} /> {FREE_MOCKS} free mocks. No card needed. Recordings stay private.
          </p>
        </div>
        <figure>
          <div className="rotate-[-1.5deg] rounded-[14px] shadow-[0_24px_48px_-12px_rgba(0,0,0,0.18)] transition-transform duration-500 ease-out hover:rotate-0">
            <ScaledCard card={SAMPLE} />
          </div>
          <figcaption className="mt-4 text-center text-sm text-ink-secondary">Sample result card, shareable in one click</figcaption>
        </figure>
      </section>

      <section className="mx-auto grid max-w-5xl items-center gap-12 px-4 py-16 lg:grid-cols-[1fr_1.1fr]">
        <div>
          <h2 className="text-[1.75rem] font-bold leading-tight text-ink text-balance">A real conversation, not a chat box</h2>
          <p className="mt-3 text-ink-secondary">
            You talk out loud and the interviewer answers in real time. It picks up on vague answers, asks about the claims
            on your CV, and you can cut in whenever you like, just like with a person.
          </p>
          <ul className="mt-6 space-y-3 text-ink">
            {LIVE_POINTS.map((p) => (
              <li key={p} className="flex items-start gap-3">
                <CheckIcon size={20} className="mt-0.5 shrink-0 text-primary" />
                {p}
              </li>
            ))}
          </ul>
        </div>
        <InterviewPreview />
      </section>

      <section>
        <div className="mx-auto max-w-5xl px-4 py-16">
          <h2 className="text-[1.75rem] font-bold text-ink">How it works</h2>
          <ol className="mt-8 grid gap-8 sm:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative">
                <span
                  className="flex size-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-white tabular-nums"
                  aria-hidden
                >
                  {i + 1}
                </span>
                <h3 className="mt-4 text-lg font-semibold text-ink">{s.title}</h3>
                <p className="mt-1 text-ink-secondary">{s.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="report" className="mx-auto max-w-5xl scroll-mt-20 px-4 py-20">
        <h2 className="max-w-xl text-[1.75rem] font-bold leading-tight text-ink text-balance">
          A report that tells you exactly what to fix
        </h2>
        <ul className="mt-8 grid gap-x-10 gap-y-4 sm:grid-cols-2">
          {REPORT_POINTS.map((p) => (
            <li key={p} className="flex items-start gap-3 text-ink">
              <CheckIcon size={20} className="mt-0.5 shrink-0 text-primary" />
              {p}
            </li>
          ))}
        </ul>
      </section>

      <section id="pricing" className="scroll-mt-20">
        <div className="mx-auto max-w-5xl px-4 py-16">
          <h2 className="text-[1.75rem] font-bold text-ink">Pricing</h2>
          <p className="mt-2 text-ink-secondary">One-time payments. No subscription, nothing renews.</p>
          <ul className="mt-8 grid gap-4 md:grid-cols-3">
            {PLANS.map((p) => (
              <li key={p.name} className="flex flex-col rounded-[16px] border border-divider bg-surface p-6 shadow-ambient">
                <h3 className="text-lg font-semibold text-ink">{p.name}</h3>
                <p className="mt-1 text-sm text-ink-secondary">{p.summary}</p>
                <p className="mt-6 flex items-baseline gap-2">
                  <span className="text-4xl font-bold tracking-[-0.02em] text-ink tabular-nums">{p.price}</span>
                  <span className="text-sm text-ink-secondary">{p.unit}</span>
                </p>
                <ul className="mt-6 flex-1 space-y-3">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2.5 text-[0.9375rem] text-ink">
                      <CheckIcon size={18} className="mt-0.5 shrink-0 text-primary" />
                      {f}
                    </li>
                  ))}
                </ul>
                <a
                  href={p.price === "$0" ? "/new" : "/new?buy=1"}
                  className={
                    p.price === "$0"
                      ? `${PRIMARY} mt-8 text-center`
                      : "mt-8 rounded-full border border-divider bg-surface px-6 py-2.5 text-center text-[0.9375rem] font-semibold text-ink transition-colors hover:border-primary"
                  }
                >
                  {p.cta}
                </a>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-ink-secondary">
            Prices in USD. Taxes are calculated at checkout by our payment provider. All purchases are final; see the{" "}
            <a href="/terms" className="text-link underline">
              terms
            </a>
            .
          </p>
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-3xl scroll-mt-20 px-4 py-20">
        <h2 className="text-[1.75rem] font-bold text-ink">Questions</h2>
        <div className="mt-6 divide-y divide-divider border-y border-divider">
          {FAQ.map((f) => (
            <details key={f.q} className="group py-4">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold text-ink [&::-webkit-details-marker]:hidden">
                {f.q}
                <PlusIcon size={20} className="shrink-0 text-ink-secondary transition-transform duration-200 group-open:rotate-45" />
              </summary>
              <p className="mt-2 max-w-[65ch] text-ink-secondary">{f.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-5xl px-4 pb-24 text-center">
        <h2 className="text-[2rem] font-bold leading-tight text-ink text-balance">Your next interview, rehearsed tonight.</h2>
        <a href="/new" className={`${PRIMARY} mt-6 inline-flex items-center gap-2 px-7 py-3`}>
          Start a free mock <ArrowRightIcon size={18} />
        </a>
      </section>
    </main>
  );
}
