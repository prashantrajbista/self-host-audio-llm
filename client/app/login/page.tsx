"use client";

import { useEffect, useState } from "react";
import { supabase, useAuth } from "@/lib/supabase";
import { BRAND, FREE_MOCKS } from "@/lib/site";
import { AlertIcon, CheckIcon, GoogleLogo, LockIcon } from "@/components/Icons";
import { ThemeToggle } from "@/components/ThemeToggle";
import { STANDALONE } from "@/lib/ui";

// only same-site paths, so a crafted ?next= can't bounce the user to another site after sign-in
function nextPath(): string {
  const next = new URLSearchParams(window.location.search).get("next") ?? "/new";
  return next.startsWith("/") && !next.startsWith("//") ? next : "/new";
}

export default function Login() {
  const session = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (session) window.location.replace(nextPath());
  }, [session]);

  // A failed Google sign-in comes back here with the reason in the URL (query or hash); show it
  // instead of silently landing on the sign-in page again.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search + "&" + window.location.hash.replace(/^#/, ""));
    const reason = params.get("error_description") || params.get("error");
    if (!reason) return;
    setError(
      /database error saving new user/i.test(reason)
        ? "We couldn't create your account (a server-side sign-up error). Please try again later, or contact us."
        : reason,
    );
    window.history.replaceState(null, "", `/login${nextPath() === "/new" ? "" : `?next=${encodeURIComponent(nextPath())}`}`);
  }, []);

  // Google returns to this page: it forwards to `next` once the session exists, or shows the error.
  const redirectTo = () => `${window.location.origin}/login?next=${encodeURIComponent(nextPath())}`;

  const google = async () => {
    setBusy(true);
    setError(null);
    const { error } = await supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo: redirectTo() } });
    if (error) {
      setError(error.message);
      setBusy(false);
    } // on success the browser is already navigating to Google
  };

  return (
    <main className={`${STANDALONE} grid lg:grid-cols-2`}>
      <title>Sign in · VoiceWire Interview</title>

      <aside className="hidden flex-col justify-between border-r border-divider bg-bg p-12 lg:flex">
        <a href="/" className="font-semibold text-ink hover:text-primary">
          {BRAND}
        </a>
        <div className="max-w-md">
          <h2 className="text-[2.125rem] font-bold leading-[1.15] tracking-[-0.02em] text-ink text-balance">
            Rehearse the interview before it counts.
          </h2>
          <ul className="mt-8 space-y-4 text-ink">
            {POINTS.map((p) => (
              <li key={p} className="flex items-start gap-3">
                <CheckIcon size={20} className="mt-0.5 shrink-0 text-primary" />
                {p}
              </li>
            ))}
          </ul>
        </div>
        <p className="flex items-center gap-2 text-sm text-ink-secondary">
          <LockIcon size={16} /> Your CV and recordings stay private to you.
        </p>
      </aside>

      <section className="flex min-h-dvh flex-col bg-surface px-4 py-6 sm:px-8">
        <div className="flex items-center justify-between">
          <a href="/" className="font-semibold text-ink hover:text-primary lg:invisible">
            {BRAND}
          </a>
          <ThemeToggle />
        </div>

        <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center py-10">
          <h1 className="text-[2.125rem] font-bold leading-[1.15] text-ink">Sign in</h1>
          <p className="mt-2 text-ink-secondary">
            New here? Signing in creates your account, with {FREE_MOCKS} free mock interviews.
          </p>

          <button
            type="button"
            onClick={() => void google()}
            disabled={busy}
            className="mt-8 flex w-full items-center justify-center gap-3 rounded-full border border-divider bg-surface px-6 py-3.5 text-[0.9375rem] font-semibold text-ink shadow-[0_1px_2px_rgba(0,0,0,0.06)] transition-colors hover:border-ink-secondary disabled:opacity-60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
            <GoogleLogo size={20} />
            {busy ? "Opening Google…" : "Continue with Google"}
          </button>

          {error && (
            <p role="alert" className="mt-4 flex items-start gap-2 text-sm text-error">
              <AlertIcon size={18} className="mt-0.5 shrink-0" />
              {error}
            </p>
          )}

          <p className="mt-8 text-xs leading-relaxed text-ink-secondary">
            By continuing you agree to our{" "}
            <a href="/terms" className="text-link underline">
              Terms
            </a>{" "}
            and{" "}
            <a href="/privacy" className="text-link underline">
              Privacy policy
            </a>
            .
          </p>
        </div>
      </section>
    </main>
  );
}

const POINTS = [
  "A live AI interviewer that asks about your real CV",
  "Follow-up questions, just like a person would ask",
  "A scored report with a stronger version of every answer",
];
