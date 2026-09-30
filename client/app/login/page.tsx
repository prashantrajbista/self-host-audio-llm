"use client";

import { useEffect, useState } from "react";
import { supabase, useAuth } from "@/lib/supabase";
import { CARD, INPUT, LABEL, PAGE, PRIMARY, SECONDARY } from "@/lib/ui";

// only same-site paths, so a crafted ?next= can't bounce the user to another site after sign-in
function nextPath(): string {
  const next = new URLSearchParams(window.location.search).get("next") ?? "/new";
  return next.startsWith("/") && !next.startsWith("//") ? next : "/new";
}

export default function Login() {
  const session = useAuth();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (session) window.location.replace(nextPath());
  }, [session]);

  const redirectTo = () => `${window.location.origin}${nextPath()}`;

  const sendLink = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const { error } = await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: redirectTo() } });
    setBusy(false);
    if (error) setError(error.message);
    else setSent(true);
  };

  const google = async () => {
    const { error } = await supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo: redirectTo() } });
    if (error) setError(error.message);
  };

  return (
    <main className={PAGE}>
      <div className={CARD}>
        <h1 className="text-2xl font-bold text-ink">Sign in</h1>
        <p className="mt-1 text-ink-secondary">Practice interviews with a live AI interviewer. Your first 2 mocks are free.</p>
        {sent ? (
          <p role="status" className="mt-6 text-ink">
            Check <span className="font-semibold">{email}</span> for a sign-in link.
          </p>
        ) : (
          <>
            <button onClick={google} className={`${SECONDARY} mt-6 w-full`}>
              Continue with Google
            </button>
            <form onSubmit={sendLink} className="mt-6">
              <label htmlFor="email" className={LABEL}>
                Or get a sign-in link by email
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={INPUT}
                placeholder="you@example.com"
              />
              <button type="submit" disabled={busy} className={`${PRIMARY} mt-3 w-full`}>
                {busy ? "Sending…" : "Email me a link"}
              </button>
            </form>
          </>
        )}
        {error && (
          <p role="alert" className="mt-4 text-sm text-error">
            {error}
          </p>
        )}
      </div>
    </main>
  );
}
