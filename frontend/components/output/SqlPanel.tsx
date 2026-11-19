"use client";

import { useCopy } from "@/hooks/useCopy";
import { tokenizeSql } from "@/lib/highlight";
import type { SqlPayload } from "@/lib/types";

const TOKEN_CLASS = {
  keyword: "sql-keyword",
  string: "sql-string",
  number: "sql-number",
  text: undefined,
} as const;

const COPY_LABEL = { idle: "Copy SQL", copied: "Copied", failed: "Couldn't copy" } as const;

function sourceLabel({ source, attempt }: SqlPayload): string {
  if (source === "button") return "Saved query";
  if (source === "fixed") return `Fixed by the assistant, attempt ${attempt}`;
  return "Written by the assistant";
}

export function SqlPanel({ sql }: { sql: SqlPayload }) {
  const { state, copy } = useCopy();

  return (
    <section aria-labelledby="sql-heading" className="flex animate-rise flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <h3 id="sql-heading" className="text-xs font-semibold uppercase tracking-wider text-muted">
          SQL
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">{sourceLabel(sql)}</span>
          <button
            type="button"
            onClick={() => void copy(sql.sql)}
            className={`flex items-center gap-1.5 rounded-md border border-line px-2 py-1 text-xs font-medium transition hover:bg-sunken ${
              state === "copied" ? "text-ok" : state === "failed" ? "text-danger" : "text-ink"
            }`}
          >
            <svg aria-hidden="true" viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              {state === "copied" ? (
                <path d="M5 12.5l4.5 4.5L19 7.5" />
              ) : (
                <>
                  <rect x="9" y="9" width="11" height="11" rx="2" />
                  <path d="M5 15V6a2 2 0 0 1 2-2h9" />
                </>
              )}
            </svg>
            <span aria-live="polite">{COPY_LABEL[state]}</span>
          </button>
        </div>
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
