import type { StepPayload } from "@/lib/types";

interface StepTrackerProps {
  steps: StepPayload[];
  running: boolean;
}

export function StepTracker({ steps, running }: StepTrackerProps) {
  if (steps.length === 0 && !running) return null;

  return (
    <section aria-labelledby="steps-heading" className="flex flex-col gap-2">
      <h3 id="steps-heading" className="text-xs font-semibold uppercase tracking-wider text-muted">
        Steps
      </h3>
      <ol className="flex flex-col gap-1.5">
        {steps.map((step, index) => (
          <li key={`${step.node}-${index}`} className="flex items-center gap-2 text-sm">
            <svg
              aria-hidden="true"
              viewBox="0 0 16 16"
              className="size-4 shrink-0 rounded-full bg-ok-soft p-0.5 text-ok"
            >
              <path
                d="M4 8.5l2.5 2.5L12 5.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span>{step.label}</span>
          </li>
        ))}
      </ol>
      {running && (
        <p className="flex items-center gap-2 text-sm text-muted" aria-live="polite">
          <span
            aria-hidden="true"
            className="size-3 shrink-0 animate-spin rounded-full border-2 border-line border-t-accent"
          />
          Working…
        </p>
      )}
    </section>
  );
}
