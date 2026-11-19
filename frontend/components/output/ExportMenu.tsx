"use client";

import { useEffect, useId, useRef, useState } from "react";
import { CSV_MIME, downloadFile, exportFileName, toCsv, toXlsx, XLSX_MIME } from "@/lib/export";
import type { RowsPayload } from "@/lib/types";

interface ExportMenuProps {
  rows: RowsPayload;
  /** Used for the file and sheet name, e.g. the conversation title. */
  name?: string | null;
}

const FORMATS = [
  { id: "xlsx", label: "Excel (.xlsx)", hint: "Opens in Excel or Google Sheets" },
  { id: "csv", label: "CSV (.csv)", hint: "Plain text, works anywhere" },
] as const;

type Format = (typeof FORMATS)[number]["id"];

export function ExportMenu({ rows, name }: ExportMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuId = useId();

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      triggerRef.current?.focus();
    };
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    rootRef.current?.querySelector<HTMLButtonElement>('[role="menuitem"]')?.focus();
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  function save(format: Format) {
    setOpen(false);
    if (format === "csv") {
      downloadFile(toCsv(rows), CSV_MIME, exportFileName(name, "csv"));
    } else {
      downloadFile(toXlsx(rows, name ?? "Results"), XLSX_MIME, exportFileName(name, "xlsx"));
    }
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? menuId : undefined}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 rounded-md border border-line px-2 py-1 text-xs font-medium text-ink transition hover:bg-sunken"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 4v11m0 0l-4-4m4 4l4-4M5 19h14" />
        </svg>
        Export
        <svg aria-hidden="true" viewBox="0 0 24 24" className={`size-3 transition ${open ? "rotate-180" : ""}`} fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div
          id={menuId}
          role="menu"
          aria-label="Export format"
          onKeyDown={(event) => {
            if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
            event.preventDefault();
            const items = Array.from(event.currentTarget.querySelectorAll<HTMLElement>('[role="menuitem"]'));
            const at = items.indexOf(document.activeElement as HTMLElement);
            const next = (at + (event.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
            items[next]?.focus();
          }}
          className="absolute right-0 top-full z-20 mt-1.5 w-56 animate-rise overflow-hidden rounded-lg border border-line bg-raised p-1 shadow-lg"
        >
          {FORMATS.map((format) => (
            <button
              key={format.id}
              type="button"
              role="menuitem"
              onClick={() => save(format.id)}
              className="flex w-full flex-col items-start rounded-md px-2.5 py-1.5 text-left transition hover:bg-sunken focus:bg-sunken focus:outline-none"
            >
              <span className="text-sm font-medium text-ink">{format.label}</span>
              <span className="text-xs text-muted">{format.hint}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
