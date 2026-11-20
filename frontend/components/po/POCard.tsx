"use client";

import { useState, type ReactNode } from "react";
import type { PODraft } from "@/lib/types";

interface POCardProps {
  draft: PODraft;
  /** True while a reply is streaming. Every action waits for it. */
  busy: boolean;
  onConfirm: (idempotencyKey: string) => void;
  onCancel: () => void;
}

const money = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatMoney = (value: string) => money.format(Number(value));
const humanise = (slot: string) => slot.replaceAll("_", " ");

const STATUS_STYLE: Record<PODraft["status"], { label: string; className: string }> = {
  open: { label: "Draft", className: "bg-warn-soft text-warn" },
  confirmed: { label: "Confirmed", className: "bg-ok-soft text-ok" },
  cancelled: { label: "Cancelled", className: "bg-sunken text-muted" },
};

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-sm font-medium">{children}</dd>
    </div>
  );
}

const notSet = <span className="font-normal text-muted">Not set</span>;

/** Confirmation card for a PO draft. Remount it (via `key`) for each new draft. */
export function POCard({ draft, busy, onConfirm, onCancel }: POCardProps) {
  // Clicks are discrete events, so React re-renders (disabling the button) before the next
  // click is handled. That makes a double click send exactly one confirm.
  const [confirming, setConfirming] = useState(false);
  const status = STATUS_STYLE[draft.status];
  const canConfirm = draft.missing.length === 0 && draft.lines.length > 0;

  function confirm() {
    setConfirming(true);
    onConfirm(draft.idempotency_key);
  }

  return (
    <section
      aria-label="Purchase order draft"
      className="flex flex-col gap-4 rounded-xl border border-line bg-panel p-4 shadow-sm"
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold">Purchase order</h3>
        <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${status.className}`}>
          {status.label}
        </span>
      </div>

      <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Detail label="Vendor">
          {draft.vendor ? (
            draft.vendor.name
          ) : (
            <span className="font-normal text-muted">Vendor not chosen yet</span>
          )}
        </Detail>
        <Detail label="Payment terms">{draft.payment_terms ?? notSet}</Detail>
        <Detail label="Deliver to">{draft.delivery_location?.name ?? notSet}</Detail>
        <Detail label="Expected delivery">{draft.expected_delivery_date ?? notSet}</Detail>
        <Detail label="Order date">{draft.placed_on}</Detail>
        <Detail label="Currency">{draft.currency}</Detail>
      </dl>

      {draft.lines.length === 0 ? (
        <p className="text-sm text-muted">No items yet.</p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="w-full border-collapse text-left text-sm">
            <thead className="bg-sunken text-xs text-muted">
              <tr>
                <th scope="col" className="px-3 py-2 font-semibold">Item</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Qty</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Unit price</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">Line total</th>
              </tr>
            </thead>
            <tbody>
              {draft.lines.map((line) => (
                <tr key={line.position} className="border-t border-line align-top">
                  <td className="px-3 py-2">
                    <span className="block font-mono text-xs text-muted">{line.item.code}</span>
                    <span className="block">{line.item.name}</span>
                    {line.warnings.map((warning) => (
                      <span key={warning} className="mt-1 block text-xs text-warn">
                        {warning}
                      </span>
                    ))}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right tabular">
                    {line.quantity} {line.unit}
                  </td>
                  <td className="px-3 py-2 text-right tabular">{line.unit_price}</td>
                  <td className="px-3 py-2 text-right tabular">{formatMoney(line.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <dl className="ml-auto grid w-full max-w-xs grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm tabular">
        <dt className="text-muted">Subtotal</dt>
        <dd className="text-right">
          {draft.currency} {formatMoney(draft.subtotal)}
        </dd>
        <dt className="text-muted">Tax</dt>
        <dd className="text-right">
          {draft.currency} {formatMoney(draft.tax_amount)}
        </dd>
        <dt className="font-semibold">Total</dt>
        <dd className="text-right font-semibold">
          {draft.currency} {formatMoney(draft.total_amount)}
        </dd>
      </dl>

      {draft.warnings.length > 0 && (
        <ul className="flex flex-col gap-1 rounded-md bg-warn-soft px-3 py-2 text-xs text-warn">
          {draft.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}

      {draft.missing.length > 0 && (
        <p className="text-sm text-muted">Still needed: {draft.missing.map(humanise).join(", ")}</p>
      )}

      {draft.status === "open" && (
        <div className="flex flex-wrap justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={busy}
            className="rounded-md px-3 py-2 text-sm font-medium text-danger hover:bg-danger-soft disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={confirm}
            disabled={busy || confirming || !canConfirm}
            className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-strong disabled:cursor-not-allowed disabled:opacity-50"
          >
            {confirming ? "Confirming…" : "Confirm"}
          </button>
        </div>
      )}
    </section>
  );
}
