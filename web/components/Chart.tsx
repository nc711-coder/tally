"use client";

import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { ChartSpec } from "@/lib/api";
import { fmtDate, fmtValue, label } from "@/lib/format";

const COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];

type Row = (string | number | null)[];

/** True on phone-sized screens, where upright bars run out of room for their labels. */
function useNarrow() {
  const [narrow, setNarrow] = useState(false);
  useEffect(() => {
    const m = window.matchMedia("(max-width: 560px)");
    const update = () => setNarrow(m.matches);
    update();
    m.addEventListener("change", update);
    return () => m.removeEventListener("change", update);
  }, []);
  return narrow;
}

export default function Chart({ spec, columns, rows }: { spec: ChartSpec; columns: string[]; rows: Row[] }) {
  const narrow = useNarrow();
  if (spec.type === "table" || !rows.length) return null;
  const kind = (c: string) => spec.formats[c] ?? "number";

  if (spec.type === "number") {
    const c = spec.y[0];
    return (
      <div className="stat">
        <div className="stat-value">{fmtValue(rows[0][0], kind(c))}</div>
        <div className="stat-label">{label(c)}</div>
      </div>
    );
  }

  const data = rows.map((r) => Object.fromEntries(columns.map((c, i) => [c, r[i]])));
  const x = spec.x as string;
  const yKind = kind(spec.y[0]);
  const tick = { fill: "var(--muted)", fontSize: 12 };
  const tooltip = (
    <Tooltip
      formatter={(v: number, name: string) => [fmtValue(v, kind(name)), label(name)]}
      labelFormatter={(v: string) => (spec.type === "line" ? fmtDate(String(v)) : String(v))}
      contentStyle={{ background: "var(--card)", border: "1px solid var(--line)", borderRadius: 8, fontSize: 13 }}
    />
  );
  const legend = spec.y.length > 1 ? <Legend formatter={(v: string) => label(v)} wrapperStyle={{ fontSize: 13 }} /> : null;

  if (spec.type === "line") {
    return (
      <div className="chart">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
            <CartesianGrid stroke="var(--line)" vertical={false} />
            <XAxis dataKey={x} tickFormatter={(v) => fmtDate(String(v))} tick={tick} tickLine={false} axisLine={{ stroke: "var(--line)" }} minTickGap={24} />
            <YAxis tickFormatter={(v) => fmtValue(v, yKind, true)} tick={tick} tickLine={false} axisLine={false} width={64} />
            {tooltip}
            {legend}
            {spec.y.map((c, i) => (
              <Line key={c} isAnimationActive={false} type="monotone" dataKey={c} stroke={COLORS[i]} strokeWidth={2.25} dot={rows.length <= 14 ? { r: 3 } : false} activeDot={{ r: 5 }} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // bars: sorted largest first, so the ranking reads at a glance
  const horizontal = spec.horizontal || (narrow && rows.length > 3);
  const sorted = [...data].sort((a, b) => Number(b[spec.y[0]] ?? 0) - Number(a[spec.y[0]] ?? 0));
  const height = horizontal ? Math.max(180, sorted.length * 34 + 40) : 280;
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={sorted} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke="var(--line)" horizontal={!horizontal} vertical={horizontal} />
          {/* axes listed directly: the chart library doesn't look inside <>...</> groups */}
          {horizontal && <XAxis type="number" tickFormatter={(v) => fmtValue(v, yKind, true)} tick={tick} tickLine={false} axisLine={false} />}
          {horizontal && <YAxis type="category" dataKey={x} tick={tick} tickLine={false} axisLine={false} width={narrow ? 104 : 150} />}
          {!horizontal && <XAxis dataKey={x} tick={tick} tickLine={false} axisLine={{ stroke: "var(--line)" }} interval={0} />}
          {!horizontal && <YAxis tickFormatter={(v) => fmtValue(v, yKind, true)} tick={tick} tickLine={false} axisLine={false} width={64} />}
          {tooltip}
          {legend}
          {spec.y.map((c, i) => (
            <Bar key={c} isAnimationActive={false} dataKey={c} fill={COLORS[i]} radius={horizontal ? [0, 4, 4, 0] : [4, 4, 0, 0]} maxBarSize={44}>
              {spec.y.length === 1 && sorted.map((_, j) => <Cell key={j} fill={j === 0 ? COLORS[0] : "var(--series-1-soft)"} />)}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
