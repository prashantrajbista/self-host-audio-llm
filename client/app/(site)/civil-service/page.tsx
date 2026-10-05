import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { BRAND, FREE_MOCKS } from "@/lib/site";
import { PRIMARY } from "@/lib/ui";

const DESCRIPTION =
  "Practise your UK Civil Service interview out loud with an AI panel. Pick your grade and the behaviours from the job advert, get follow-up questions like a real panel, and a 1 to 7 score for each behaviour.";

export const metadata: Metadata = {
  title: `Civil Service interview practice, by voice · ${BRAND}`,
  description: DESCRIPTION,
  alternates: { canonical: "/civil-service" },
  openGraph: { title: "Civil Service interview practice, out loud, at your grade", description: DESCRIPTION },
};

const SUCCESS_PROFILES = "https://www.gov.uk/government/publications/success-profiles";

const FAQ = [
  {
    q: "Is this an official Civil Service tool?",
    a: "No. It's an independent practice tool, not affiliated with or endorsed by the UK Civil Service. It's built on the Success Profiles framework that GOV.UK publishes for candidates.",
  },
  {
    q: "Which grades does it cover?",
    a: "AA and AO, EO, HEO and SEO, and Grade 7 and Grade 6. Questions and scoring use the behaviour examples GOV.UK publishes for each level.",
  },
  {
    q: "How is it scored?",
    a: "Each behaviour, strengths and experience answer gets a score from 1 (not demonstrated) to 7 (outstanding), the scale departments publish for candidates. Panels usually need 4 or more on each, so the report shows which answers clear that bar and which indicators you missed.",
  },
  {
    q: "Should I rehearse my strengths answers?",
    a: "No. GOV.UK advises against rehearsing strengths answers because panels want your first, natural response. The mock mixes in unseen strengths questions so you get used to answering them on the spot.",
  },
];

const JSON_LD = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQ.map((f) => ({ "@type": "Question", name: f.q, acceptedAnswer: { "@type": "Answer", text: f.a } })),
};

// SEO landing page for Civil Service interview practice. Claims must match the pack (packs/civil_service.toml) and the report.
export default function CivilServicePractice() {
  return (
    <LegalPage title="Practise your Civil Service interview out loud, at your grade" dated={false}>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD).replace(/</g, "\\u003c") }} />
      <p>
        Knowing STAR and having good examples isn&apos;t the same as giving a clear answer to a panel, especially when
        the follow-up questions start. {BRAND} lets you rehearse a Civil Service interview by voice, then scores it the way
        panels do.
      </p>

      <h2>How it works</h2>
      <ul>
        <li>
          <strong>Set it up like your real interview.</strong> Pick your grade, tick the behaviours from the job advert,
          and choose whether strengths and experience questions are included. Paste the advert if you have it.
        </li>
        <li>
          <strong>Talk to an AI panel chair.</strong> One question per behaviour, at your grade. When your answer misses
          something the grade expects, you get a follow-up, like a real panel. You can ask for a moment to think.
        </li>
        <li>
          <strong>Get scored 1 to 7.</strong> Every answer is scored against the{" "}
          <a href={SUCCESS_PROFILES}>Success Profiles</a> behaviour examples for your grade, with the indicators you showed,
          the ones you missed, and a stronger version of your answer built from your own facts.
        </li>
        <li>
          <strong>Hear how you came across.</strong> Pace, filler words and answer length, plus a replay of the call.
        </li>
      </ul>

      <h2>Why not just use ChatGPT?</h2>
      <p>
        A general chatbot asks generic questions and gives generic scores. This mock knows what each behaviour looks like at
        EO, HEO, SEO or Grade 7, aims its follow-ups at what your answer left out, and reports on the same 1 to 7 scale a
        panel uses.
      </p>

      <h2>Questions</h2>
      {FAQ.map((f) => (
        <div key={f.q}>
          <h3>{f.q}</h3>
          <p>{f.a}</p>
        </div>
      ))}

      <h2>What it costs</h2>
      <p>
        {FREE_MOCKS} mocks are free, no card needed. After that you pay once, with no subscription and nothing that renews:
        see <a href="/#pricing">pricing</a>.
      </p>

      <p className="mt-8">
        <a href="/new?pack=civil_service" className={`${PRIMARY} inline-block !text-white !no-underline`}>
          Start a free Civil Service mock
        </a>
      </p>

      <p className="mt-8 text-sm text-ink-secondary">
        Not affiliated with or endorsed by the UK Civil Service. Behaviour examples and the strengths dictionary are from{" "}
        <a href={SUCCESS_PROFILES}>GOV.UK Success Profiles</a>, used under the Open Government Licence v3.0.
      </p>
    </LegalPage>
  );
}
