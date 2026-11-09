import type { ChartSpec } from "@/lib/api";
import { fmtValue, label } from "@/lib/format";

export default function ResultTable({ columns, rows, spec, truncated }: {
  columns: string[]; rows: (string | number | null)[][]; spec: ChartSpec | null | undefined; truncated?: boolean;
}) {
  const kind = (c: string) => spec?.formats?.[c] ?? "text";
  const numeric = (c: string) => ["money", "percent", "number"].includes(kind(c));
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((c) => <th key={c} className={numeric(c) ? "num" : ""}>{label(c)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, 200).map((r, i) => (
            <tr key={i}>
              {r.map((v, j) => <td key={j} className={numeric(columns[j]) ? "num" : ""}>{fmtValue(v, kind(columns[j]))}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
      {(rows.length > 200 || truncated) && (
        <p className="note">Showing the first {Math.min(rows.length, 200)} rows{truncated ? " (results are capped at 1,000)" : ""}.</p>
      )}
    </div>
  );
}
