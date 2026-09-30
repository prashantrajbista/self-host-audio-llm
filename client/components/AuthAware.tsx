"use client";

// Public pages adapt to a signed-in visitor: app links instead of "Sign in" / "Start a free mock".
// Until the session is known (read from the browser, no network) the slot keeps its size, so nothing flickers.
import { ArrowRightIcon } from "@/components/Icons";
import { ProfileMenu, profileOf } from "@/components/ProfileMenu";
import { useAuth } from "@/lib/supabase";
import { PRIMARY } from "@/lib/ui";

export function HeaderAuthLinks() {
  const auth = useAuth();
  if (auth === undefined) return <span className="inline-block w-16" aria-hidden />;
  if (!auth) {
    return (
      <a href="/login" className="font-semibold text-ink hover:text-primary">
        Sign in
      </a>
    );
  }
  return (
    <>
      <a href="/new" className="rounded-full bg-primary px-4 py-1.5 font-semibold text-white transition-colors hover:bg-primary-hover">
        New interview
      </a>
      <ProfileMenu session={auth} />
    </>
  );
}

export function HeroActions() {
  const auth = useAuth();
  const signedIn = !!auth;
  return (
    <div className={`mt-8 flex flex-wrap items-center gap-4 ${auth === undefined ? "invisible" : ""}`}>
      <a href="/new" className={`${PRIMARY} inline-flex items-center gap-2 px-7 py-3`}>
        {signedIn ? "Start an interview" : "Start a free mock"} <ArrowRightIcon size={18} />
      </a>
      {auth ? (
        <>
          <a href="/history" className="font-semibold text-ink underline decoration-divider hover:decoration-ink">
            Your interviews
          </a>
          <p className="w-full text-sm text-ink-secondary">Welcome back, {profileOf(auth).firstName}.</p>
        </>
      ) : (
        <a href="#report" className="font-semibold text-ink underline decoration-divider hover:decoration-ink">
          See what you get
        </a>
      )}
    </div>
  );
}
