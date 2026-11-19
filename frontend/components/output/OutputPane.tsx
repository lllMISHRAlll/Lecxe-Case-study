"use client";

import { ChartView } from "@/components/charts/ChartView";
import { OutputSkeleton } from "@/components/layout/Skeletons";
import type { OutputState } from "@/stores/chatStore";
import type { ReactNode } from "react";
import { DataTable } from "./DataTable";
import { SqlPanel } from "./SqlPanel";
import { StepTracker } from "./StepTracker";

interface OutputPaneProps {
  output: OutputState;
  /** The current turn is still filling this pane. */
  running: boolean;
  /** A conversation is being loaded: show placeholders. */
  loading?: boolean;
  /** Rendered above the query results, for example the PO confirmation card. */
  poSlot?: ReactNode;
  /** Names exported files, e.g. the conversation title. */
  title?: string | null;
}

/** True when the results pane has anything to show. */
export function hasOutput(output: OutputState): boolean {
  return Boolean(
    output.turn > 0 || output.steps.length || output.sql || output.rows || output.chart || output.poDraft,
  );
}

export function OutputPane({ output, running, loading = false, poSlot, title }: OutputPaneProps) {
  return (
    <section
      aria-label="Results"
      className="flex min-h-0 min-w-0 animate-pane-in flex-col gap-5 overflow-y-auto bg-panel p-4 sm:p-6"
    >
      {loading ? (
        <OutputSkeleton />
      ) : (
        <>
          {/* Keyed by turn so each new answer replays its steps from the start. */}
          <StepTracker key={output.turn} steps={output.steps} running={running} />
          {poSlot}
          {output.chart && <ChartView spec={output.chart} />}
          {output.rows && <DataTable rows={output.rows} exportName={output.question ?? title} />}
          {output.sql && <SqlPanel sql={output.sql} />}
        </>
      )}
    </section>
  );
}
