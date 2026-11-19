const compact = new Intl.NumberFormat("en-IN", { notation: "compact", maximumFractionDigits: 1 });

/** Short Indian-style numbers for chart axes: 1.5K, 45L, 1.5Cr. */
export function compactNumber(value: unknown): string {
  return typeof value === "number" ? compact.format(value).replace(/\s/g, "") : String(value);
}
