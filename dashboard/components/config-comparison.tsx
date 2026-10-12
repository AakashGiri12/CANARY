"use client";

import { useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { type ComparePointOut, compareConfigs } from "@/lib/api";

const PALETTE = ["#34d399", "#22d3ee", "#a78bfa", "#fbbf24", "#f472b6", "#fb7185"];

function shortLabel(label: string) {
  return label.replace(" (No Defense)", "").replace(" + Defense", "+Def");
}

function LineChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: ComparePointOut & { asrPct: number; utilityPct: number } }[];
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/95 px-3 py-2 font-mono text-xs text-slate-200 shadow-xl">
      <div className="mb-1 font-semibold text-slate-100">{p.config_label}</div>
      <div className="text-rose-300">ASR: {p.asrPct.toFixed(0)}%</div>
      <div className="text-emerald-300">Utility: {p.utilityPct.toFixed(0)}%</div>
    </div>
  );
}

export function ConfigComparison() {
  const [points, setPoints] = useState<ComparePointOut[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    if (loading) return;
    setLoading(true);
    try {
      const result = await compareConfigs();
      setPoints(result);
    } finally {
      setLoading(false);
    }
  }

  const chartData =
    points?.map((p) => ({
      ...p,
      asrPct: p.asr_rate * 100,
      utilityPct: p.utility_rate * 100,
      shortLabel: shortLabel(p.config_label),
    })) ?? [];

  return (
    <div className="flex w-full flex-col gap-5 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-mono text-sm font-semibold uppercase tracking-widest text-slate-200">
            Utility / ASR across configs
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            One live static-attack battery per config. The ideal config
            keeps Utility near 100% while ASR stays near 0%.
          </p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="shrink-0 rounded-lg border border-slate-700 bg-slate-900/60 px-3.5 py-2 font-mono text-xs font-semibold text-slate-200 transition-colors hover:border-emerald-400/60 hover:text-emerald-300 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {loading ? "Running all configs…" : "Run full comparison"}
        </button>
      </div>

      {points && (
        <>
          <div>
            <h3 className="mb-2 font-mono text-xs font-semibold uppercase tracking-widest text-slate-400">
              Per-config performance
            </h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 10, right: 20, bottom: 30, left: 0 }}
                >
                  <CartesianGrid stroke="rgba(148,163,184,0.1)" />
                  <XAxis
                    dataKey="shortLabel"
                    tick={{ fill: "#64748b", fontSize: 10, fontFamily: "monospace" }}
                    stroke="rgba(148,163,184,0.3)"
                    angle={-20}
                    textAnchor="end"
                    height={50}
                    interval={0}
                  />
                  <YAxis
                    domain={[0, 100]}
                    unit="%"
                    tick={{ fill: "#64748b", fontSize: 11, fontFamily: "monospace" }}
                    stroke="rgba(148,163,184,0.3)"
                  />
                  <Tooltip content={<LineChartTooltip />} cursor={{ stroke: "rgba(148,163,184,0.2)" }} />
                  <Legend
                    wrapperStyle={{ fontFamily: "monospace", fontSize: 11, color: "#94a3b8" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="asrPct"
                    name="Attack Success Rate"
                    stroke="#fb7185"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#fb7185" }}
                  />
                  <Line
                    type="monotone"
                    dataKey="utilityPct"
                    name="Task Utility"
                    stroke="#34d399"
                    strokeWidth={2}
                    dot={{ r: 4, fill: "#34d399" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <ul className="flex flex-col gap-1.5">
            {points.map((p, i) => (
              <li
                key={p.config_key}
                className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs"
              >
                <span className="flex items-center gap-2 text-slate-300">
                  <span
                    className="size-2 rounded-full"
                    style={{ background: PALETTE[i % PALETTE.length] }}
                  />
                  {p.config_label}
                </span>
                <span className="font-mono text-slate-400">
                  ASR {(p.asr_rate * 100).toFixed(0)}% · Utility{" "}
                  {(p.utility_rate * 100).toFixed(0)}%
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {!points && !loading && (
        <p className="font-mono text-xs text-slate-600">
          No comparison run yet — click &ldquo;Run full comparison&rdquo; to
          plot every config&rsquo;s real ASR/Utility point.
        </p>
      )}
    </div>
  );
}
