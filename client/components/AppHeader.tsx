"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { BuyPanel } from "@/components/BuyPanel";
import { CreditIcon } from "@/components/Icons";
import { ProfileMenu } from "@/components/ProfileMenu";
import { ThemeToggle } from "@/components/ThemeToggle";
import { BRAND } from "@/lib/site";
import { gatewayFetch, useAuth, type Profile } from "@/lib/supabase";

const CREDITS_EVENT = "credits-changed";
// Call after anything that changes credits (a purchase landed, an interview started).
export const refreshCredits = () => window.dispatchEvent(new Event(CREDITS_EVENT));

const NAV = [
  { href: "/new", label: "New interview" },
  { href: "/history", label: "History" },
];

export function AppHeader() {
  const session = useAuth();
  const uid = session?.user.id;
  const path = usePathname();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [buyOpen, setBuyOpen] = useState(false);

  useEffect(() => {
    if (!uid) return;
    const load = () => void gatewayFetch<Profile>("/me").then(setProfile, () => {});
    load();
    window.addEventListener(CREDITS_EVENT, load);
    return () => window.removeEventListener(CREDITS_EVENT, load);
  }, [uid]);

  const credits = profile ? (profile.has_pass ? "Unlimited" : `${profile.credits} left`) : null;

  return (
    <header className="sticky top-0 z-10 border-b border-divider bg-bg/85 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4 sm:gap-6">
        <a href="/" className="mr-auto shrink-0 font-semibold text-ink hover:text-primary">
          {BRAND}
        </a>
        <nav aria-label="Main" className="flex items-center gap-1 text-sm">
          {NAV.map((item) => {
            const active = path === item.href || (item.href === "/history" && path.startsWith("/report"));
            return (
              <a
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`rounded-full px-3 py-1.5 transition-colors hover:bg-divider/40 ${
                  active ? "font-semibold text-ink" : "text-ink-secondary"
                }`}
              >
                {item.label}
              </a>
            );
          })}
        </nav>
        {credits && (
          <button
            onClick={() => setBuyOpen(true)}
            title="Your mock interviews. Buy more."
            className="flex items-center gap-1.5 rounded-full border border-divider bg-surface px-3 py-1.5 text-sm text-ink tabular-nums transition-colors hover:border-primary"
          >
            <CreditIcon size={16} className="text-primary" />
            {credits}
          </button>
        )}
        <ThemeToggle />
        {session && (
          <ProfileMenu
            session={session}
            extra={profile && (profile.has_pass ? "Unlimited mocks active" : `${profile.credits} mock${profile.credits === 1 ? "" : "s"} left`)}
          />
        )}
      </div>
      <BuyPanel open={buyOpen} onClose={() => setBuyOpen(false)} />
    </header>
  );
}
