"use client";

import { useState } from "react";
import { sendFeedback } from "@/lib/api";

interface FeedbackButtonsProps {
  messageId: string;
  value?: 1 | -1;
  onSaved: (score: 1 | -1) => void;
}

const OPTIONS = [
  { score: 1, label: "Helpful", icon: "M7 10v10M7 10l4-7a2 2 0 0 1 3 2l-1 5h5a2 2 0 0 1 2 2l-2 7a2 2 0 0 1-2 1H7" },
  { score: -1, label: "Not helpful", icon: "M17 14V4m0 10-4 7a2 2 0 0 1-3-2l1-5H6a2 2 0 0 1-2-2l2-7a2 2 0 0 1 2-1h9" },
] as const;

export function FeedbackButtons({ messageId, value, onSaved }: FeedbackButtonsProps) {
  const [failed, setFailed] = useState(false);

  async function save(score: 1 | -1) {
    setFailed(false);
    try {
      await sendFeedback(messageId, score);
      onSaved(score);
    } catch {
      setFailed(true);
    }
  }

  return (
    <div className="flex items-center gap-1">
      {OPTIONS.map(({ score, label, icon }) => (
        <button
          key={label}
          type="button"
          aria-label={label}
          aria-pressed={value === score}
          onClick={() => save(score)}
          className={`rounded-md p-1 transition hover:bg-sunken ${
            value === score ? "text-accent" : "text-muted"
          }`}
        >
          <svg aria-hidden="true" viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d={icon} />
          </svg>
        </button>
      ))}
      {failed && <span className="text-xs text-danger">Couldn&apos;t save feedback.</span>}
    </div>
  );
}
