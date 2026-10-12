"use client";

import { useEffect, useState } from "react";
import { FlaskConical } from "lucide-react";
import { type ClassifierResultOut, classifierResults } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  const good = status === "validated";
  return (
    <span
      className={
        "rounded-full px-2.5 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider " +
        (good
          ? "bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/30"
          : "bg-amber-500/10 text-amber-300 ring-1 ring-inset ring-amber-500/30")
      }
    >
      {status}
    </span>
  );
}

export function ClassifierDefense() {
  const [results, setResults] = useState<ClassifierResultOut[] | null>(null);

  useEffect(() => {
    classifierResults().then(setResults);
  }, []);

  return (
    <div className="flex w-full flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur">
      <div className="flex items-center gap-2">
        <FlaskConical className="size-4 text-purple-300" />
        <h2 className="font-mono text-sm font-semibold uppercase tracking-widest text-slate-200">
          Trained classifier defense
        </h2>
      </div>
      {results ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {results.map((r) => (
            <div
              key={r.model_label}
              className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-slate-300">
                  {r.model_label}
                </span>
                <StatusBadge status={r.status} />
              </div>
              <div className="flex gap-4">
                <div>
                  <div className="font-mono text-xl font-bold text-slate-100">
                    {(r.accuracy * 100).toFixed(0)}%
                  </div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                    Accuracy
                  </div>
                </div>
                <div>
                  <div className="font-mono text-xl font-bold text-slate-100">
                    {(r.f1 * 100).toFixed(0)}%
                  </div>
                  <div className="font-mono text-[10px] uppercase tracking-widest text-slate-500">
                    F1
                  </div>
                </div>
              </div>
              <p className="text-[11px] text-slate-500">{r.note}</p>
            </div>
          ))}
        </div>
      ) : (
        <p className="font-mono text-xs text-slate-600">loading…</p>
      )}
    </div>
  );
}
