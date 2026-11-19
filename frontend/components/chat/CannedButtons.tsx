"use client";

import { useQuery } from "@tanstack/react-query";
import { getCanned } from "@/lib/api";
import type { CannedQuery } from "@/lib/types";

interface CannedButtonsProps {
  onRun: (query: CannedQuery) => void;
  disabled?: boolean;
  /** "grid": equal cards with a description (empty chat). "row": equal chips in one line. */
  variant?: "grid" | "row";
}

const CARD =
  "group flex h-full min-h-[4.5rem] w-full flex-col items-start justify-between gap-1 rounded-xl border border-line bg-raised px-3.5 py-3 text-left shadow-sm transition hover:-translate-y-px hover:border-accent hover:shadow-md disabled:pointer-events-none disabled:opacity-50";
const CHIP =
  "flex h-8 w-40 shrink-0 items-center justify-center truncate rounded-lg border border-line bg-raised px-3 text-xs font-medium text-ink transition hover:border-accent hover:bg-accent-soft hover:text-accent-strong disabled:cursor-not-allowed disabled:opacity-50";

export function CannedButtons({ onRun, disabled = false, variant = "row" }: CannedButtonsProps) {
  const canned = useQuery({ queryKey: ["canned"], queryFn: getCanned });

  if (canned.isError) {
    return <p className="text-xs text-muted">Couldn&apos;t load suggested questions.</p>;
  }
  const queries = canned.data ?? [];

  if (variant === "grid") {
    return (
      <div aria-label="Suggested questions" className="grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2">
        {queries.map((query) => (
          <button
            key={query.id}
            type="button"
            aria-label={query.label}
            aria-describedby={`canned-${query.id}`}
            disabled={disabled}
            onClick={() => onRun(query)}
            className={CARD}
          >
            <span className="text-sm font-semibold text-ink group-hover:text-accent-strong">
              {query.label}
            </span>
            <span id={`canned-${query.id}`} className="line-clamp-2 text-xs leading-snug text-muted">
              {query.description}
            </span>
          </button>
        ))}
      </div>
    );
  }

  return (
    <div
      aria-label="Suggested questions"
      className="no-scrollbar -mx-1 flex snap-x gap-2 overflow-x-auto px-1 pb-0.5"
    >
      {queries.map((query) => (
        <button
          key={query.id}
          type="button"
          title={query.description}
          disabled={disabled}
          onClick={() => onRun(query)}
          className={`${CHIP} snap-start`}
        >
          {query.label}
        </button>
      ))}
    </div>
  );
}
