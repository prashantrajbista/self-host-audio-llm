import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { BRAND, FREE_MOCKS } from "@/lib/site";
import { PRIMARY } from "@/lib/ui";

const DESCRIPTION =
  "Practice behavioral and HR interview questions out loud with a live AI interviewer. Questions from your CV, follow-ups on vague answers, and a scored report. Free to start.";

export const metadata: Metadata = {
  title: `Behavioral interview practice with AI · ${BRAND}`,
  description: DESCRIPTION,
  alternates: { canonical: "/behavioral-interview-practice" },
  openGraph: { title: "Behavioral interview practice, out loud, with AI", description: DESCRIPTION },
};

// SEO landing page for "behavioral interview practice". Claims must match the home page and the report.
export default function BehavioralPractice() {
  return (
    <LegalPage title="Behavioral interview practice, out loud" dated={false}>
      <p>
        Behavioral questions (&quot;tell me about a time you…&quot;) come up in almost every interview, for every role. Reading
        sample answers helps, but the hard part is saying a clear, specific answer out loud under pressure. {BRAND} lets you
        rehearse exactly that with a live AI interviewer.
      </p>

      <h2>How a practice interview works</h2>
      <ul>
        <li>
          <strong>Upload your CV and paste the job post.</strong> Questions come from a curated bank of behavioral and HR
          screening questions plus your own experience and the role you want, at the level you pick.
        </li>
        <li>
          <strong>Talk, don&apos;t type.</strong> The interviewer asks by voice and answers in real time. It follows up when an
          answer is vague, and you can interrupt it, like with a person. About 20 minutes.
        </li>
        <li>
          <strong>Get scored on every answer.</strong> Each answer is graded on structure, specificity, impact, reflection and
          relevance, with a stronger version to learn from.
        </li>
        <li>
          <strong>See how you spoke.</strong> Pace, filler words, answer length and response time, plus a replay of the call.
        </li>
      </ul>

      <h2>Private by design</h2>
      <p>
        Your CV is anonymized before the AI reads it, and your side of each recording is stored with your voice disguised.
        See the <a href="/privacy">privacy policy</a> for details.
      </p>

      <h2>What it costs</h2>
      <p>
        {FREE_MOCKS} mocks are free, no card needed. After that you pay once, with no subscription and nothing that renews:
        see <a href="/#pricing">pricing</a>.
      </p>

      <p className="mt-8">
        <a href="/new" className={`${PRIMARY} inline-block !text-white !no-underline`}>
          Start a free mock
        </a>
      </p>
    </LegalPage>
  );
}
