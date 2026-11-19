"use client";

import type { ReactElement } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartSpec } from "@/lib/types";

/** Series colours, chosen to stay distinguishable and readable on white. */
export const SERIES_COLORS = ["#0f6e6a", "#c2410c", "#4f46e5", "#a16207", "#be185d", "#0369a1"];

interface ChartViewProps {
  spec: ChartSpec;
  /** Fixed size, used in tests. Without it the chart fills its container. */
  width?: number;
  height?: number;
}

const AXIS = { fontSize: 11, fill: "#5b6776" };

function renderChart(spec: ChartSpec, width?: number, height?: number): ReactElement | null {
  const size = { width, height };
  const series = spec.y.map((key, i) => ({ key, color: SERIES_COLORS[i % SERIES_COLORS.length] }));

  switch (spec.type) {
    case "bar":
      return (
        <BarChart {...size} data={spec.data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={spec.x} tick={AXIS} />
          <YAxis tick={AXIS} />
          <Tooltip />
          {series.length > 1 && <Legend />}
          {series.map((s) => (
            <Bar key={s.key} dataKey={s.key} fill={s.color} radius={[3, 3, 0, 0]} />
          ))}
        </BarChart>
      );
    case "horizontal_bar":
      return (
        <BarChart {...size} data={spec.data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" tick={AXIS} />
          <YAxis type="category" dataKey={spec.x} tick={AXIS} width={140} />
          <Tooltip />
          {series.length > 1 && <Legend />}
          {series.map((s) => (
            <Bar key={s.key} dataKey={s.key} fill={s.color} radius={[0, 3, 3, 0]} />
          ))}
        </BarChart>
      );
    case "line":
      return (
        <LineChart {...size} data={spec.data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey={spec.x} tick={AXIS} />
          <YAxis tick={AXIS} />
          <Tooltip />
          {series.length > 1 && <Legend />}
          {series.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} stroke={s.color} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      );
    case "pie":
      return (
        <PieChart {...size}>
          <Tooltip />
          <Legend />
          <Pie data={spec.data} dataKey={spec.y[0]} nameKey={spec.x} outerRadius="75%" isAnimationActive={false}>
            {spec.data.map((_, i) => (
              <Cell key={i} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
            ))}
          </Pie>
        </PieChart>
      );
    case "scatter":
      return (
        <ScatterChart {...size}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" dataKey={spec.x} name={spec.x} tick={AXIS} />
          <YAxis type="number" dataKey={spec.y[0]} name={spec.y[0]} tick={AXIS} />
          <Tooltip />
          <Scatter data={spec.data} fill={SERIES_COLORS[0]} />
        </ScatterChart>
      );
    case "table":
      return null;
  }
}

export function ChartView({ spec, width, height }: ChartViewProps) {
  const chart = renderChart(spec, width, height);
  if (!chart) return null;

  return (
    <section aria-labelledby="chart-heading" className="flex flex-col gap-2" data-testid={`chart-${spec.type}`}>
      <h3 id="chart-heading" className="text-sm font-semibold">
        {spec.title}
      </h3>
      {width && height ? (
        chart
      ) : (
        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            {chart}
          </ResponsiveContainer>
        </div>
      )}
    </section>
  );
}
