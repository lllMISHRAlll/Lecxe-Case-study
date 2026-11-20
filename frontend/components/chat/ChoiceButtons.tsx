"use client";

import { useState } from "react";
import type { Choice, ChoicesPayload } from "@/lib/types";

interface ChoiceButtonsProps {
  choices: ChoicesPayload;
  /** Always an array: one option for a single pick, one or more after Submit in multi mode. */
  onChoose: (choices: Choice[]) => void;
  disabled?: boolean;
}

const BASE =
  "rounded-md border px-3 py-1.5 text-xs font-medium transition disabled:cursor-not-allowed disabled:opacity-50";

export function ChoiceButtons({ choices, onChoose, disabled = false }: ChoiceButtonsProps) {
  const [picked, setPicked] = useState<string[]>([]);
  const multiple = choices.multiple === true;

  const toggle = (id: string) =>
    setPicked((current) =>
      current.includes(id) ? current.filter((x) => x !== id) : [...current, id],
    );
  const allPicked = picked.length === choices.options.length;
  const selected = choices.options.filter((o) => picked.includes(o.id));

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs text-muted">{choices.prompt}</p>
      {multiple && <p className="text-xs text-muted">Select one or more, then submit.</p>}
      <div className="flex flex-wrap gap-2">
        {choices.options.map((option) => {
          const on = picked.includes(option.id);
          return (
            <button
              key={option.id}
              type="button"
              disabled={disabled}
              aria-pressed={multiple ? on : undefined}
              onClick={() => (multiple ? toggle(option.id) : onChoose([option]))}
              className={`${BASE} ${
                on
                  ? "border-accent bg-accent text-white"
                  : "border-accent text-accent hover:bg-accent-soft"
              }`}
            >
              {multiple && <span aria-hidden="true">{on ? "✓ " : ""}</span>}
              {option.label}
            </button>
          );
        })}
      </div>
      {multiple && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={disabled}
            onClick={() => setPicked(allPicked ? [] : choices.options.map((o) => o.id))}
            className={`${BASE} border-line text-muted hover:bg-accent-soft`}
          >
            {allPicked ? "Clear all" : "Select all"}
          </button>
          <button
            type="button"
            disabled={disabled || selected.length === 0}
            onClick={() => onChoose(selected)}
            className={`${BASE} border-accent bg-accent text-white hover:opacity-90`}
          >
            Submit{selected.length > 0 ? ` (${selected.length})` : ""}
          </button>
        </div>
      )}
    </div>
  );
}
