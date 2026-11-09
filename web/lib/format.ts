const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

export function isDate(v: unknown): v is string {
  return typeof v === "string" && /^\d{4}-\d{2}(-\d{2})?/.test(v);
}

/** "2026-07-01" -> "Jul 2026" (dates in this data are always month or quarter starts, or days). */
export function fmtDate(v: string, withDay = false): string {
  const [y, m, d] = v.slice(0, 10).split("-");
  const month = MONTHS[Number(m) - 1] ?? m;
  return withDay && d && d !== "01" ? `${month} ${Number(d)}, ${y}` : `${month} ${y}`;
}

export function fmtValue(v: unknown, kind: string = "number", short = false): string {
  if (v === null || v === undefined) return "–";
  if (typeof v !== "number") return isDate(v) ? fmtDate(v, true) : String(v);
  if (kind === "percent") return `${v.toLocaleString("en-US", { maximumFractionDigits: 1 })}%`;
  if (kind === "money") {
    if (short && v === 0) return "$0";
    if (short && Math.abs(v) >= 1000) {
      return "$" + (Math.abs(v) >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : `${(v / 1e3).toFixed(v >= 1e4 ? 0 : 1)}K`);
    }
    // cents kept everywhere except chart axes, so the big number and the table match the sentence exactly
    return v.toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  if (short && Math.abs(v) >= 10000) return `${(v / 1e3).toFixed(0)}K`;
  return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

/** "avg_order_value" -> "Avg order value" */
export function label(col: string): string {
  const s = col.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
