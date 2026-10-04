import type { Metadata } from "next";
import { ArrowRightIcon, CheckIcon, LockIcon, PlusIcon } from "@/components/Icons";
import { HeroActions } from "@/components/AuthAware";
import { InterviewPreview } from "@/components/InterviewPreview";
import { ScaledCard } from "@/components/ScaledCard";
import type { PublicCard } from "@/lib/share";
import { BRAND, FREE_MOCKS, PLANS, RETENTION_DAYS, SITE_URL, TAGLINE } from "@/lib/site";
import { PRIMARY } from "@/lib/ui";

// Illustrative only (labelled as a sample on the page): what a shared result card looks like.
const SAMPLE: PublicCard = {
  brand: BRAND,
  score: 78,
  verdict: "Solid answers",
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
  "An overall score and how strong your answers were for the level you chose",
  "Skill scores: structure, specificity, impact, reflection, relevance",
  "How you spoke: pace, filler words, answer length, response time",
  "Every answer replayable, with what worked, what to fix, and a stronger version",
  "For questions about your CV: whether your answer backed up what your CV claims",
];

// What people complain about in other interview prep tools, and where we stand. Kept generic (no product names):
// their plans change often and a stale claim about a named product is worse than none.
const COMPARE: { row: string; us: string; tools: string; coaches: string }[] = [
  { row: "How you pay", us: "Once, per pack or pass", tools: "Monthly subscription", coaches: "Per session" },
  { row: "Auto-renewal", us: "Never", tools: "Usually, often hard to cancel", coaches: "No" },
  { row: "Follow-up questions", us: "Yes, live by voice", tools: "Often fixed question lists", coaches: "Yes" },
  { row: "Scores what you say, not just how", us: "Yes, 5 skills per answer", tools: "Often delivery only", coaches: "Yes" },
  { row: "Session fails or drops", us: "Reconnects, or your credit comes back", tools: "Varies", coaches: "Reschedule" },
  { row: "Your CV and voice", us: "CV anonymized, voice disguised", tools: "Usually stored as uploaded", coaches: "Shared with the coach" },
  { row: "Price per mock", us: "From under $2", tools: "Bundled in the plan", coaches: "$150 and up" },
];

// The two privacy claims. Keep them exactly as true as the code: server/agent/anonymize.py (CV) and
// server/services/voice_anon.py (stored recording only; the live call is still transcribed from your real voice).
const PRIVACY = [
  {
    title: "The AI never sees your name",
    body: "Before anything reads your CV, your name, email, phone, address and LinkedIn, GitHub or other profile links and IDs are swapped for placeholders. Your experience, employers and skills stay, so the questions are still about you. The original file is never stored.",
    sample: ["[NAME]", "[EMAIL]", "[PHONE]", "[LINK]"],
  },
  {
    title: "Your replay is voice-disguised",
    body: "Before your recording is stored, the pitch and character of your voice are shifted so it sounds like someone else. Your words, pace and tone stay, so you can still review how you came across.",
    sample: ["Same words", "Same pace", "Different voice"],
  },
];

const PRICING_PROMISES = ["One-time payment", "Nothing renews", "Technical problem? Credit back automatically"];

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
    a: `Only you, and even we don't keep the identifying parts: your CV is anonymized before the AI reads it and the original file is never stored, and your side of each recording is stored with your voice disguised. Nothing is public unless you choose to share a result card, which never includes your transcript, recording or CV. Deleted items and recordings older than ${RETENTION_DAYS} days are permanently removed.`,
  },
  {
    q: "Do I need special equipment?",
    a: "A microphone and a quiet room. Headphones help, so your speakers don't echo the interviewer back into your mic.",
  },
  {
    q: "Will I be charged again later?",
    a: "No. Every purchase is a one-time payment. There is no subscription, and the 30-day pass simply ends after 30 days without renewing.",
  },
  {
    q: "What if my connection drops mid-interview?",
    a: "The call reconnects on its own and the interviewer picks up where you left off. If it can't reconnect, your answers so far are still scored, and a session that breaks on our side or ends before you answer anything gives its credit back automatically.",
  },
  {
    q: "Can I get a refund?",
    a: `No. All purchases are final, so try your ${FREE_MOCKS} free mocks first. If an interview fails or ends before you answer anything, its credit goes back to your account automatically.`,
  },
];

export const metadata: Metadata = { alternates: { canonical: "/" } };

// Structured data so search engines can show price and FAQ rich results.
const JSON_LD = [
  {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: BRAND,
    url: SITE_URL,
    description: TAGLINE,
    applicationCategory: "EducationalApplication",
    operatingSystem: "Web",
    offers: PLANS.map((p) => ({ "@type": "Offer", name: p.name, price: p.price.replace("$", ""), priceCurrency: "USD" })),
  },
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQ.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
  },
];

export default function Landing() {
  return (
    <main>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD).replace(/</g, "\\u003c") }} />
      <section className="mx-auto grid max-w-5xl items-center gap-12 px-4 pb-20 pt-10 sm:pt-16 lg:grid-cols-[1.05fr_1fr]">
        <div>
          <p className="mb-3 text-sm font-semibold text-primary">AI mock interview, by voice</p>
          <h1 className="text-[2.75rem] font-bold leading-[1.05] tracking-[-0.02em] text-ink text-balance sm:text-6xl">
            Rehearse the interview before it counts.
          </h1>
          <p className="mt-5 max-w-lg text-lg text-ink-secondary">
            Talk to a live AI interviewer that asks about your real CV, pushes for specifics, and scores every answer. About
            20 minutes, entirely by voice.
          </p>
          <HeroActions />
          <p className="mt-4 flex items-center gap-2 text-sm text-ink-secondary">
            <LockIcon size={16} /> {FREE_MOCKS} free mocks, no card needed. Then pay once: no subscription, no auto-renew.
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

      <section id="privacy" className="mx-auto max-w-5xl scroll-mt-20 px-4 py-16">
        <h2 className="max-w-xl text-[1.75rem] font-bold leading-tight text-ink text-balance">
          Practise as yourself. Your name and voice stay out of it.
        </h2>
        <ul className="mt-8 grid gap-4 md:grid-cols-2">
          {PRIVACY.map((p) => (
            <li key={p.title} className="rounded-[16px] border border-divider bg-surface p-6 shadow-ambient">
              <LockIcon size={20} className="text-primary" />
              <h3 className="mt-3 text-lg font-semibold text-ink">{p.title}</h3>
              <p className="mt-2 text-ink-secondary">{p.body}</p>
              <ul className="mt-4 flex flex-wrap gap-2" aria-hidden>
                {p.sample.map((t) => (
                  <li key={t} className="rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">
                    {t}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
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
          <h2 className="text-[1.75rem] font-bold text-ink">Pricing, no subscription</h2>
          <p className="mt-2 text-ink-secondary">One-time payments. No subscription, nothing renews.</p>
          <ul className="mt-4 flex flex-wrap gap-2">
            {PRICING_PROMISES.map((p) => (
              <li key={p} className="flex items-center gap-1.5 rounded-full border border-divider px-3 py-1 text-sm text-ink">
                <CheckIcon size={16} className="text-primary" />
                {p}
              </li>
            ))}
          </ul>
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

      <section id="compare" className="mx-auto max-w-5xl scroll-mt-20 px-4 py-16">
        <h2 className="text-[1.75rem] font-bold text-ink">How it compares</h2>
        <p className="mt-2 max-w-xl text-ink-secondary">
          The usual options for interview practice, side by side. No trial that turns into a subscription.
        </p>
        <div className="mt-8 overflow-x-auto">
          <table className="w-full min-w-[36rem] text-left text-[0.9375rem]">
            <thead>
              <tr className="border-b border-divider text-sm text-ink-secondary">
                <th scope="col" className="py-3 pr-4 font-normal">
                  <span className="sr-only">Feature</span>
                </th>
                <th scope="col" className="py-3 pr-4 font-semibold text-primary">{BRAND}</th>
                <th scope="col" className="py-3 pr-4 font-semibold">Typical AI practice app</th>
                <th scope="col" className="py-3 font-semibold">Human mock coach</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-divider">
              {COMPARE.map((c) => (
                <tr key={c.row}>
                  <th scope="row" className="py-3 pr-4 font-semibold text-ink">{c.row}</th>
                  <td className="py-3 pr-4 text-ink">{c.us}</td>
                  <td className="py-3 pr-4 text-ink-secondary">{c.tools}</td>
                  <td className="py-3 text-ink-secondary">{c.coaches}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-6 flex items-start gap-2 text-sm text-ink-secondary">
          <LockIcon size={16} className="mt-0.5 shrink-0" />
          Your CV, recordings and transcripts are never used to train AI models. Recordings are deleted after {RETENTION_DAYS}{" "}
          days, and you can delete anything sooner.
        </p>
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
