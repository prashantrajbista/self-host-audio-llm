"use client";

import { useEffect, useState } from "react";
import { AlertIcon, CheckIcon } from "@/components/Icons";
import { gatewayFetch, useAuth } from "@/lib/supabase";
import { INPUT, LABEL, PRIMARY } from "@/lib/ui";

const TOPICS = [
  { id: "question", label: "A question" },
  { id: "problem", label: "Something isn't working" },
  { id: "payment", label: "Payments" },
  { id: "privacy", label: "My data and privacy" },
  { id: "other", label: "Something else" },
];

// Saved to the gateway's contact_messages table (POST /contact).
export function ContactForm() {
  const auth = useAuth();
  const [form, setForm] = useState({ name: "", email: "", topic: "question", message: "", website: "" });
  const [status, setStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [error, setError] = useState<string | null>(null);
  const set = (patch: Partial<typeof form>) => setForm((f) => ({ ...f, ...patch }));

  const signedInEmail = auth?.user.email;
  useEffect(() => {
    if (signedInEmail) setForm((f) => (f.email ? f : { ...f, email: signedInEmail }));
  }, [signedInEmail]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus("sending");
    setError(null);
    try {
      await gatewayFetch("/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      setStatus("sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't send your message. Please email us instead.");
      setStatus("idle");
    }
  };

  if (status === "sent") {
    return (
      <div role="status" className="rounded-[12px] border border-divider bg-surface p-6">
        <p className="flex items-center gap-2 font-semibold text-ink">
          <CheckIcon size={20} className="text-primary" /> Message sent
        </p>
        <p className="mt-1 text-ink-secondary">Thanks, {form.name.split(" ")[0]}. We&apos;ll reply to {form.email}.</p>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4 rounded-[12px] border border-divider bg-surface p-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="c-name" className={LABEL}>
            Name
          </label>
          <input id="c-name" required maxLength={100} autoComplete="name" value={form.name} onChange={(e) => set({ name: e.target.value })} className={INPUT} />
        </div>
        <div>
          <label htmlFor="c-email" className={LABEL}>
            Email
          </label>
          <input
            id="c-email"
            type="email"
            required
            maxLength={254}
            autoComplete="email"
            value={form.email}
            onChange={(e) => set({ email: e.target.value })}
            className={INPUT}
          />
        </div>
      </div>
      <div>
        <label htmlFor="c-topic" className={LABEL}>
          What is it about?
        </label>
        <select id="c-topic" value={form.topic} onChange={(e) => set({ topic: e.target.value })} className={INPUT}>
          {TOPICS.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="c-message" className={LABEL}>
          Message
        </label>
        <textarea
          id="c-message"
          required
          minLength={10}
          maxLength={5000}
          rows={6}
          value={form.message}
          onChange={(e) => set({ message: e.target.value })}
          className={INPUT}
          placeholder="For a problem with an interview, tell us roughly when it happened and what you saw."
        />
      </div>
      {/* honeypot: invisible to people and screen readers, filled in by bots */}
      <div aria-hidden className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label htmlFor="c-website">Website</label>
        <input id="c-website" tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => set({ website: e.target.value })} />
      </div>
      {error && (
        <p role="alert" className="flex items-start gap-2 text-sm text-error">
          <AlertIcon size={18} className="mt-0.5 shrink-0" />
          {error}
        </p>
      )}
      <button type="submit" disabled={status === "sending"} className={`${PRIMARY} w-full sm:w-auto`}>
        {status === "sending" ? "Sending…" : "Send message"}
      </button>
    </form>
  );
}
