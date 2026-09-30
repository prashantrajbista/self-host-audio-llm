"use client";

import { useEffect, useRef, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

export function profileOf(session: Session) {
  const meta = session.user.user_metadata ?? {};
  const email = session.user.email ?? "";
  const name: string = meta.full_name || meta.name || email.split("@")[0];
  const avatar: string | undefined = meta.avatar_url || meta.picture;
  const initials = name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]!.toUpperCase())
    .join("");
  return { name, email, avatar, initials, firstName: name.split(/\s+/)[0] };
}

function Avatar({ src, initials, size }: { src?: string; initials: string; size: number }) {
  const [broken, setBroken] = useState(false);
  if (src && !broken) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- remote Google avatar, no image optimisation needed
      <img
        src={src}
        alt=""
        width={size}
        height={size}
        referrerPolicy="no-referrer" // Google avatar URLs can refuse requests that carry a referrer
        onError={() => setBroken(true)}
        className="rounded-full object-cover"
        style={{ width: size, height: size }}
      />
    );
  }
  return (
    <span
      className="flex items-center justify-center rounded-full bg-primary text-xs font-semibold text-white"
      style={{ width: size, height: size }}
    >
      {initials}
    </span>
  );
}

// Avatar button with a small menu: who's signed in, app links, sign out.
export function ProfileMenu({ session, extra }: { session: Session; extra?: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const p = profileOf(session);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const item = "block w-full rounded-[8px] px-3 py-2 text-left text-sm text-ink transition-colors hover:bg-divider/40";
  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Account: ${p.name}`}
        className="flex rounded-full ring-offset-2 ring-offset-bg transition-shadow hover:ring-2 hover:ring-divider focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
      >
        <Avatar src={p.avatar} initials={p.initials} size={32} />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-11 z-20 w-64 rounded-[12px] border border-divider bg-surface p-2 shadow-[0_12px_32px_-8px_rgba(0,0,0,0.2)] motion-safe:animate-fade-in"
        >
          <div className="flex items-center gap-3 px-3 py-2">
            <Avatar src={p.avatar} initials={p.initials} size={36} />
            <div className="min-w-0">
              <p className="truncate font-semibold text-ink">{p.name}</p>
              <p className="truncate text-xs text-ink-secondary">{p.email}</p>
            </div>
          </div>
          {extra && <div className="px-3 pb-2 text-sm text-ink-secondary">{extra}</div>}
          <div className="my-1 h-px bg-divider" />
          <a role="menuitem" href="/new" className={item}>
            New interview
          </a>
          <a role="menuitem" href="/history" className={item}>
            My interviews
          </a>
          <div className="my-1 h-px bg-divider" />
          <button
            role="menuitem"
            type="button"
            onClick={() => void supabase.auth.signOut().then(() => window.location.assign("/"))}
            className={item}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
