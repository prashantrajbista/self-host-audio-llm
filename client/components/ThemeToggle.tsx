"use client";

import { useEffect, useState } from "react";
import { MoonIcon, SunIcon } from "@/components/Icons";
import { applyTheme, currentTheme, type Theme } from "@/lib/theme";

// Switches between light and dark; shows the mode you'd switch to.
export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme | null>(null); // null until mounted: the server can't know it
  useEffect(() => setTheme(currentTheme()), []);

  const next: Theme = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      onClick={() => {
        applyTheme(next);
        setTheme(next);
      }}
      aria-label={`Switch to ${next} mode`}
      title={`Switch to ${next} mode`}
      className="flex size-9 shrink-0 items-center justify-center rounded-full text-ink-secondary transition-colors hover:bg-divider/40 hover:text-ink"
    >
      {theme === null ? <span className="size-[18px]" /> : theme === "dark" ? <SunIcon size={18} /> : <MoonIcon size={18} />}
    </button>
  );
}
