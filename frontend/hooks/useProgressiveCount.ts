"use client";

import { useEffect, useState } from "react";

interface Options {
  /** Reveal one item at a time. When false, everything shows at once (e.g. a restored chat). */
  animate: boolean;
  intervalMs?: number;
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * How many of `total` items to show. Items that arrive in a burst are revealed one after
 * another, so the user can follow each step instead of seeing them all pop in together.
 */
export function useProgressiveCount(total: number, { animate, intervalMs = 160 }: Options): number {
  const instant = !animate || prefersReducedMotion();
  const [shown, setShown] = useState(() => (instant ? total : Math.min(total, 1)));

  useEffect(() => {
    if (instant || shown >= total) return;
    const timer = setTimeout(() => setShown((n) => n + 1), intervalMs);
    return () => clearTimeout(timer);
  }, [instant, shown, total, intervalMs]);

  return instant ? total : Math.min(shown, total);
}
