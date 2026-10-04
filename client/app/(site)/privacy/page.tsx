import type { Metadata } from "next";
import { LegalPage } from "@/components/LegalPage";
import { BRAND, OPERATOR, RETENTION_DAYS, SUPPORT_EMAIL } from "@/lib/site";

export const metadata: Metadata = { title: `Privacy policy · ${BRAND}` };

// Template drafted from how the product actually works; have it reviewed before launch.
export default function Privacy() {
  const mail = <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>;
  return (
    <LegalPage title="Privacy policy">
      <p>
        {BRAND} is run by {OPERATOR} (&ldquo;we&rdquo;). This policy explains what we collect when you practise interviews
        with us, why, who else handles it, and how long we keep it. Questions: {mail}.
      </p>

      <h2>What we collect</h2>
      <ul>
        <li>
          <strong>Account:</strong> your name and email address from your Google account when you sign in with Google.
        </li>
        <li>
          <strong>Your CV, anonymized:</strong> we extract the text from the file you upload, replace your name, email,
          phone number, address, LinkedIn, GitHub and other profile links or usernames, and ID numbers with placeholders on our own servers, and keep only that
          anonymized text and a structured summary (roles, skills, achievements) built from it. The original file is
          never stored. Employers, schools, job titles and dates are kept, because the interview questions come from them.
        </li>
        <li>
          <strong>Interviews:</strong> a recording of each interview in which your side is voice-disguised (pitch and
          formant shifted) on our own servers (your original audio is held in memory only while it is processed, and
          never stored), the
          transcript, the role, level and job post you entered, and the scored report. During the live interview your
          speech is transcribed from your real voice; only the stored replay is disguised. Your words in the transcript
          and replay are unchanged, so anything identifying you say out loud stays in them.
        </li>
        <li>
          <strong>Payments:</strong> which plan you bought, the amount and the transaction reference. Card details go
          directly to our payment provider; we never see or store them.
        </li>
        <li>
          <strong>Messages to us:</strong> what you send through the contact form (name, email, topic and message), kept so
          we can answer and follow up.
        </li>
        <li>
          <strong>Technical data:</strong> server logs (such as IP address and errors) used to keep the service secure and
          working.
        </li>
      </ul>

      <h2>Why we use it</h2>
      <ul>
        <li>To run your mock interviews: generate questions from your CV, hold the conversation, and score your answers.</li>
        <li>To let you replay interviews and see your history.</li>
        <li>To process payments and give you the interviews you bought.</li>
        <li>To keep the service secure and fix problems.</li>
      </ul>
      <p>
        We do not sell your data, show ads, or use your CV, recordings or transcripts to train AI models.
      </p>

      <h2>Who else handles your data</h2>
      <ul>
        <li>
          <strong>Supabase</strong>: sign-in.
        </li>
        <li>
          <strong>Microsoft Azure</strong>: hosts our servers and the private storage for voice-disguised recordings.
        </li>
        <li>
          <strong>Microsoft Azure AI Foundry</strong>, our AI model provider: receives your anonymized CV text (never your
          name or contact details), the job post and interview transcripts to run the interviewer and score your answers,
          and your live speech audio during the interview to transcribe it and to voice the interviewer. It processes this
          to give us a response and does not use it to train its models under our agreement with it.
        </li>
        <li>
          <strong>Paddle</strong>: our reseller and merchant of record. It handles checkout, payment, tax and invoicing
          under its own privacy policy.
        </li>
      </ul>
      <p>
        The recording we keep for your replay is disguised on our own servers: your side is pitch- and
        formant-shifted so it sounds like a different voice before it is stored, and your original audio is never
        stored or sent anywhere for that step. The disguise is not irreversible, so treat the replay as private.
      </p>

      <h2>What becomes public</h2>
      <p>
        Nothing, unless you share a result card. A shared card shows only the fields you choose (for example your score,
        role and initials) and never includes your transcript, recording, CV or job post. You can stop sharing at any time,
        and the link stops working immediately.
      </p>

      <h2>How long we keep it</h2>
      <ul>
        <li>Interview recordings are permanently deleted {RETENTION_DAYS} days after the interview.</li>
        <li>
          When you delete a CV or an interview, it disappears from your account straight away and is permanently removed,
          including stored files, within {RETENTION_DAYS} days.
        </li>
        <li>Transcripts and reports of interviews you keep stay available to you while your account exists.</li>
        <li>Payment records are kept for as long as tax and accounting law requires.</li>
      </ul>

      <h2>Your rights</h2>
      <p>
        You can ask us for a copy of your data, to correct it, or to delete your account and everything in it. Email {mail}{" "}
        from the address you sign in with and we will respond within 30 days. Depending on where you live you may also have
        the right to complain to a data protection authority.
      </p>

      <h2>Cookies and storage</h2>
      <p>
        We only use what the service needs to work: your browser stores your sign-in session. We use no advertising or
        tracking cookies. During checkout, Paddle may set its own cookies for fraud prevention.
      </p>

      <h2>Security</h2>
      <p>
        Data is sent over encrypted connections. Anonymized recordings are kept in private storage that only your account
        can reach through the service, and replay links expire after an hour.
      </p>

      <h2>Children</h2>
      <p>The service is not intended for anyone under 16.</p>

      <h2>Changes</h2>
      <p>
        If we change this policy we will update the date above, and tell you by email if the change is significant.
      </p>
    </LegalPage>
  );
}
