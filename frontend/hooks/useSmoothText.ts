"use client";

import { useEffect, useRef, useState } from "react";

const FRAME_MS = 16;
/** Characters revealed per frame: a steady minimum, faster when far behind. */
const MIN_STEP = 2;
const CATCH_UP_FRAMES = 5;

function reducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Streams text in at a steady pace instead of in network-sized bursts.
 * Finished messages (not active, nothing to reveal) are shown at once.
 */
export function useSmoothText(target: string, active: boolean): string {
  const [shown, setShown] = useState(() => (active ? "" : target));
  const shownRef = useRef(shown);
  shownRef.current = shown;

  useEffect(() => {
    // Replaced or unrelated text (e.g. answer_replace, history load): show it directly.
    if (!target.startsWith(shownRef.current) || reducedMotion()) {
      setShown(target);
      return;
    }
    if (!active && shownRef.current === "" && target !== "") {
      setShown(target);
      return;
    }
    if (shownRef.current.length >= target.length) return;

    const timer = setInterval(() => {
      const current = shownRef.current;
      const remaining = target.length - current.length;
      if (remaining <= 0) {
        clearInterval(timer);
        return;
      }
      const step = Math.max(MIN_STEP, Math.ceil(remaining / CATCH_UP_FRAMES));
      const next = target.slice(0, current.length + step);
      shownRef.current = next;
      setShown(next);
    }, FRAME_MS);
    return () => clearInterval(timer);
  }, [target, active]);

  return shown;
}
