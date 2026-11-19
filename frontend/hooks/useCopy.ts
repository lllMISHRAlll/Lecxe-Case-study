"use client";

import { useEffect, useState } from "react";

export type CopyState = "idle" | "copied" | "failed";

function copyWithSelection(text: string): boolean {
  const area = document.createElement("textarea");
  area.value = text;
  area.setAttribute("readonly", "");
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.append(area);
  area.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    area.remove();
  }
}

/** Copies text to the clipboard and reports the outcome for a couple of seconds. */
export function useCopy(resetMs = 2000) {
  const [state, setState] = useState<CopyState>("idle");

  useEffect(() => {
    if (state === "idle") return;
    const timer = setTimeout(() => setState("idle"), resetMs);
    return () => clearTimeout(timer);
  }, [state, resetMs]);

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setState("copied");
    } catch {
      // Clipboard API missing or refused (e.g. plain http): fall back to a selection copy.
      setState(copyWithSelection(text) ? "copied" : "failed");
    }
  }

  return { state, copy };
}
