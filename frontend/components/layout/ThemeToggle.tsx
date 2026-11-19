"use client";

import { useEffect, useState } from "react";
import { applyTheme, prefersDark, readTheme, resolveTheme, saveTheme, type ResolvedTheme } from "@/lib/theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<ResolvedTheme>(() =>
    typeof window === "undefined" ? "light" : resolveTheme(readTheme(), prefersDark()),
  );

  useEffect(() => applyTheme(theme), [theme]);

  function toggle() {
    const next: ResolvedTheme = theme === "dark" ? "light" : "dark";
    saveTheme(next);
    setTheme(next);
  }

  const toDark = theme !== "dark";
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={toDark ? "Switch to dark mode" : "Switch to light mode"}
      title={toDark ? "Dark mode" : "Light mode"}
      className="grid size-9 shrink-0 place-items-center rounded-lg border border-line text-muted transition hover:bg-sunken hover:text-ink"
    >
      {toDark ? (
        <svg aria-hidden="true" viewBox="0 0 24 24" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />
        </svg>
      ) : (
        <svg aria-hidden="true" viewBox="0 0 24 24" className="size-[18px]" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
        </svg>
      )}
    </button>
  );
}
