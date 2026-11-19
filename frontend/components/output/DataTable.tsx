import type { RowsPayload } from "@/lib/types";
import { ExportMenu } from "./ExportMenu";

const numberFormat = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

function formatCell(value: string | number | boolean | null): string {
  if (value === null || value === "") return "—";
  if (typeof value === "number") return numberFormat.format(value);
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return value;
}

interface DataTableProps {
  rows: RowsPayload;
  /** Names the exported file, e.g. the conversation title. */
  exportName?: string | null;
}

export function DataTable({ rows, exportName }: DataTableProps) {
  const count = `${rows.row_count} ${rows.row_count === 1 ? "row" : "rows"}`;

  return (
    <section aria-labelledby="data-heading" className="flex min-w-0 animate-rise flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h3 id="data-heading" className="text-xs font-semibold uppercase tracking-wider text-muted">
          Data
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted tabular">{count}</span>
          {rows.rows.length > 0 && <ExportMenu rows={rows} name={exportName} />}
        </div>
      </div>
      {rows.truncated && (
        <p className="rounded-md bg-warn-soft px-3 py-2 text-xs text-warn">
          Showing the first {rows.rows.length} rows. The result was cut at {rows.row_count} rows.
        </p>
      )}
      {rows.rows.length === 0 ? (
        <p className="text-sm text-muted">No rows returned.</p>
      ) : (
        <div className="max-h-96 overflow-auto rounded-lg border border-line">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="sticky top-0 bg-sunken">
              <tr>
                {rows.columns.map((column) => (
                  <th
                    key={column.name}
                    scope="col"
                    className="whitespace-nowrap border-b border-line px-3 py-2 text-xs font-semibold text-muted"
                  >
                    {column.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.rows.map((row, rowIndex) => (
                <tr key={rowIndex} className="odd:bg-panel even:bg-sunken/60">
                  {row.map((cell, cellIndex) => (
                    <td
                      key={cellIndex}
                      className={`border-b border-line px-3 py-1.5 ${
                        typeof cell === "number" ? "text-right tabular" : ""
                      }`}
                    >
                      {formatCell(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
