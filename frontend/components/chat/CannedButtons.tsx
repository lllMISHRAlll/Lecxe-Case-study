"use client";

import { useQuery } from "@tanstack/react-query";
import { getCanned } from "@/lib/api";
import type { CannedQuery } from "@/lib/types";

interface CannedButtonsProps {
  onRun: (query: CannedQuery) => void;
  disabled?: boolean;
}

export function CannedButtons({ onRun, disabled = false }: CannedButtonsProps) {
  const canned = useQuery({ queryKey: ["canned"], queryFn: getCanned });

  if (canned.isError) {
    return <p className="text-xs text-muted">Couldn&apos;t load suggested questions.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2" aria-label="Suggested questions">
      {(canned.data ?? []).map((query) => (
        <button
          key={query.id}
          type="button"
          title={query.description}
          disabled={disabled}
          onClick={() => onRun(query)}
          className="rounded-full border border-line bg-panel px-3 py-1 text-xs font-medium text-ink transition hover:border-accent hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-50"
        >
          {query.label}
        </button>
      ))}
    </div>
  );
}
