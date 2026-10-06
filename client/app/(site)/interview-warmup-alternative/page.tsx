import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { BRAND, FREE_MOCKS, FREE_NOW, PAYMENTS } from "@/lib/site";
import { PRIMARY } from "@/lib/ui";

const DESCRIPTION =
  "Google Interview Warmup shut down in April 2026. Practise out loud with a live AI interviewer instead: questions from your CV, follow-ups, and a scored report. Free to start.";

export const metadata: Metadata = {
  title: `Google Interview Warmup alternative · ${BRAND}`,
  description: DESCRIPTION,
  alternates: { canonical: "/interview-warmup-alternative" },
  openGraph: { title: "A free Google Interview Warmup alternative", description: DESCRIPTION },
};

// SEO landing page for people looking for a replacement after Interview Warmup closed. Facts only about Warmup.
export default function WarmupAlternative() {
  return (
    <LegalPage title="A Google Interview Warmup alternative" dated={false}>
      <p>
        Google Interview Warmup was a free tool for practising answers to common interview questions. Google shut it down
        in April 2026. If you used it to get comfortable answering out loud, {BRAND} picks up where it left off, and goes
        further.
      </p>

      <h2>What&apos;s the same</h2>
      <ul>
        <li>You practise by speaking, not typing.</li>
        <li>{PAYMENTS ? `You can start for free: ${FREE_MOCKS} full mock interviews, no card needed.` : FREE_NOW}</li>
        <li>Feedback after every answer, so you know what to work on.</li>
      </ul>

      <h2>What&apos;s different</h2>
      <ul>
        <li>
          <strong>A real conversation.</strong> A live AI interviewer asks the questions, follows up when an answer is vague,
          and you can interrupt it, like with a person.
        </li>
        <li>
          <strong>Questions about you.</strong> Upload your CV and paste the job post; questions come from your own
          experience and the role you want.
        </li>
        <li>
          <strong>Scores on what you said.</strong> Each answer is graded on structure, specificity, impact, reflection and
          relevance, plus how you spoke: pace, filler words and answer length.
        </li>
        <li>
          <strong>A stronger version of each answer</strong>, a replay of the call, and your progress across mocks.
        </li>
      </ul>

      <h2>What it costs</h2>
      {PAYMENTS ? (
        <p>
          {FREE_MOCKS} mocks are free. After that you pay once, with no subscription and nothing that renews: see{" "}
          <a href="/#pricing">pricing</a>.
        </p>
      ) : (
        <p>{FREE_NOW}</p>
      )}

      <p className="mt-8">
        <a href="/new" className={`${PRIMARY} inline-block !text-white !no-underline`}>
          Start a free mock
        </a>
      </p>
    </LegalPage>
  );
}
