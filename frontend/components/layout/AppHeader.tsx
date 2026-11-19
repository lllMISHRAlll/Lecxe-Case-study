"use client";

import { useState } from "react";
import { logout } from "@/lib/api";
import type { User } from "@/lib/types";
import { ThemeToggle } from "./ThemeToggle";

interface AppHeaderProps {
  user: User;
  onLoggedOut: () => void;
}

export function AppHeader({ user, onLoggedOut }: AppHeaderProps) {
  const [leaving, setLeaving] = useState(false);

  async function handleLogout() {
    setLeaving(true);
    try {
      await logout();
    } catch {
      // The session may already be gone. Leaving the app is still the right outcome.
    } finally {
      onLoggedOut();
    }
  }

  return (
    <header className="flex items-center justify-between gap-4 border-b border-line bg-panel px-4 py-3 sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <span
          aria-hidden="true"
          className="grid size-8 shrink-0 place-items-center rounded-md bg-accent text-sm font-bold text-on-accent"
        >
          PA
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold sm:text-base">
            Hey {user.name}, {user.role_label} welcome
          </p>
          <p className="truncate text-xs text-muted">Procurement Assistant</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-2">
      <ThemeToggle />
      <button
        type="button"
        onClick={handleLogout}
        disabled={leaving}
        className="h-9 shrink-0 rounded-lg border border-line px-3 text-sm font-medium text-ink transition hover:bg-sunken disabled:opacity-60"
      >
        Log out
      </button>
      </div>
    </header>
  );
}
