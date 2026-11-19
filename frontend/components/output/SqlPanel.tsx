import { tokenizeSql } from "@/lib/highlight";
import type { SqlPayload } from "@/lib/types";

const TOKEN_CLASS = {
  keyword: "sql-keyword",
  string: "sql-string",
  number: "sql-number",
  text: undefined,
} as const;

function sourceLabel({ source, attempt }: SqlPayload): string {
  if (source === "button") return "Saved query";
  if (source === "fixed") return `Fixed by the assistant, attempt ${attempt}`;
  return "Written by the assistant";
}

export function SqlPanel({ sql }: { sql: SqlPayload }) {
  return (
    <section aria-labelledby="sql-heading" className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h3 id="sql-heading" className="text-xs font-semibold uppercase tracking-wider text-muted">
          SQL
        </h3>
        <span className="text-xs text-muted">{sourceLabel(sql)}</span>
      </div>
      <pre className="overflow-x-auto rounded-lg border border-line bg-sunken p-3 text-xs leading-relaxed">
        <code className="font-mono">
          {tokenizeSql(sql.sql).map((token, index) => (
            <span key={index} className={TOKEN_CLASS[token.kind]}>
              {token.text}
            </span>
          ))}
        </code>
      </pre>
    </section>
  );
}
