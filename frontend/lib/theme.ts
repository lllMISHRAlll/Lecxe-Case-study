/** Light / dark theme. "system" follows the OS setting. Stored per browser. */

export type ThemeChoice = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";

export const THEME_KEY = "pa-theme";
const CHOICES: ThemeChoice[] = ["light", "dark", "system"];

export function resolveTheme(choice: ThemeChoice, prefersDark: boolean): ResolvedTheme {
  if (choice === "system") return prefersDark ? "dark" : "light";
  return choice;
}

export function readTheme(): ThemeChoice {
  try {
    const stored = localStorage.getItem(THEME_KEY);
    return CHOICES.includes(stored as ThemeChoice) ? (stored as ThemeChoice) : "system";
  } catch {
    return "system";
  }
}

export function saveTheme(choice: ThemeChoice): void {
  try {
    localStorage.setItem(THEME_KEY, choice);
  } catch {
    // Storage can be blocked (private mode). The theme still applies for this visit.
  }
}

export function prefersDark(): boolean {
  return typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)").matches
    : false;
}

export function applyTheme(theme: ResolvedTheme): void {
  document.documentElement.dataset.theme = theme;
}

/**
 * Inline script for <head>: sets data-theme before the first paint so there is no flash of
 * the wrong theme. Mirrors readTheme/resolveTheme.
 */
export const THEME_BOOT_SCRIPT = `(function(){try{var c=localStorage.getItem("${THEME_KEY}");var d=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches;var t=c==="dark"||c==="light"?c:(d?"dark":"light");document.documentElement.dataset.theme=t;}catch(e){}})();`;
