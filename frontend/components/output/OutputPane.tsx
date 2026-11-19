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
  running: boolean;
  /** A conversation is being loaded: show placeholders instead of the empty screen. */
  loading?: boolean;
  /** Rendered above the query results, for example the PO confirmation card. */
  poSlot?: ReactNode;
}

export function OutputPane({ output, running, loading = false, poSlot }: OutputPaneProps) {
  const isEmpty =
    !running &&
    output.steps.length === 0 &&
    !output.sql &&
    !output.rows &&
    !output.chart &&
    !output.poDraft;

  return (
    <section
      aria-label="Results"
      className="flex min-h-0 min-w-0 flex-col gap-5 overflow-y-auto bg-panel p-4 sm:p-6"
    >
      {loading ? (
        <OutputSkeleton />
      ) : isEmpty ? (
        <div className="m-auto flex max-w-sm flex-col items-center gap-2 py-16 text-center">
          <p className="text-base font-semibold">Results appear here</p>
          <p className="text-sm text-muted">
            Ask a question or pick a suggested question. The steps, SQL, data and chart will show
            up in this panel as the answer streams in.
          </p>
        </div>
      ) : (
        <>
          <StepTracker steps={output.steps} running={running} />
          {poSlot}
          {output.chart && <ChartView spec={output.chart} />}
          {output.rows && <DataTable rows={output.rows} />}
          {output.sql && <SqlPanel sql={output.sql} />}
        </>
      )}
    </section>
  );
}
