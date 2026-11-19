"use client";

import { useState } from "react";
import { useProgressiveCount } from "@/hooks/useProgressiveCount";
import type { StepPayload, StepStatus } from "@/lib/types";

interface StepTrackerProps {
  steps: StepPayload[];
  running: boolean;
}

const DOT_CLASS: Record<StepStatus, string> = {
  done: "bg-ok-soft text-ok",
  warn: "bg-warn-soft text-warn",
  error: "bg-danger-soft text-danger",
};

function StatusIcon({ status }: { status: StepStatus }) {
  return (
    <span
      aria-hidden="true"
      className={`step-pop relative z-10 grid size-5 shrink-0 place-items-center rounded-full ring-4 ring-panel ${DOT_CLASS[status]}`}
    >
      <svg viewBox="0 0 16 16" className="size-3" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        {status === "done" && <path d="M4 8.5l2.5 2.5L12 5.5" />}
        {status === "warn" && <path d="M8 4.5v4.5M8 11.5v.01" />}
        {status === "error" && <path d="M5 5l6 6M11 5l-6 6" />}
      </svg>
    </span>
  );
}

/** A vertical timeline of the work behind an answer, revealed one step at a time. */
export function StepTracker({ steps, running }: StepTrackerProps) {
  // Animate once this run has been seen live; a restored conversation shows its steps at once.
  const [live, setLive] = useState(running);
  if (running && !live) setLive(true);
  const shown = useProgressiveCount(steps.length, { animate: live });

  if (steps.length === 0 && !running) return null;

  const visible = steps.slice(0, shown);
  const catchingUp = shown < steps.length;
  const working = running || catchingUp;
  const count = `${steps.length} ${steps.length === 1 ? "step" : "steps"}`;

  return (
    <section aria-labelledby="steps-heading" className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <h3 id="steps-heading" className="text-xs font-semibold uppercase tracking-wider text-muted">
          Steps
        </h3>
        {!working && <span className="animate-fade text-xs text-muted">{count}</span>}
      </div>
      <ol className="relative flex flex-col gap-2.5">
        {visible.map((step, index) => {
          const status = step.status ?? "done";
          const last = index === visible.length - 1 && !working;
          return (
            <li
              key={`${step.node}-${index}`}
              data-status={status}
              className="relative flex animate-rise items-center gap-3 text-sm"
            >
              {!last && (
                <span aria-hidden="true" className="step-line absolute left-[9px] top-5 -bottom-2.5 w-0.5 bg-line" />
              )}
              <StatusIcon status={status} />
              <span className={status === "error" ? "text-danger" : status === "warn" ? "text-warn" : ""}>
                {step.label}
              </span>
            </li>
          );
        })}
      </ol>
      {working && (
        <p className="-mt-0.5 flex animate-fade items-center gap-3 text-sm text-muted" aria-live="polite">
          <span aria-hidden="true" className="relative grid size-5 shrink-0 place-items-center">
            <span className="absolute inset-0 animate-ping rounded-full bg-accent/25" />
            <span className="size-2.5 rounded-full bg-accent" />
          </span>
          <span className="shimmer-text">Working…</span>
        </p>
      )}
    </section>
  );
}
