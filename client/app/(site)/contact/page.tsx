import type { Metadata } from "next";
import { ContactForm } from "@/components/ContactForm";
import { LegalPage } from "@/components/LegalPage";
import { BRAND, SUPPORT_EMAIL } from "@/lib/site";

export const metadata: Metadata = { title: `Contact · ${BRAND}` };

export default function Contact() {
  const mail = <a href={`mailto:${SUPPORT_EMAIL}`}>{SUPPORT_EMAIL}</a>;
  return (
    <LegalPage title="Contact" dated={false}>
      <p>
        Send us a message below, or email {mail}. We read every message and usually reply within two working days.
      </p>

      <div className="not-prose my-8">
        <ContactForm />
      </div>

      <h2>Helpful to include</h2>
      <ul>
        <li>The email address you sign in with.</li>
        <li>For a payment question: the order reference from your receipt.</li>
        <li>For a problem with an interview: roughly when it happened, and what you saw.</li>
      </ul>

      <h2>Your data</h2>
      <p>
        To get a copy of your data or delete your account, write to us from the address you sign in with. See the{" "}
        <a href="/privacy">privacy policy</a> for what we keep and for how long.
      </p>
    </LegalPage>
  );
}
