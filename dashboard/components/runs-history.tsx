"use client";

import { useCallback, useEffect, useState } from "react";
import { History, RotateCw } from "lucide-react";
import { type HistoryEntryOut, runsHistory } from "@/lib/api";

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime();
  const diffSec = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (diffSec < 5) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.floor(diffHr / 24)}d ago`;
}

export function RunsHistory() {
  const [entries, setEntries] = useState<HistoryEntryOut[] | null>(null);
  const [loading, setLoading] = useState(true);

  // No setState call in the synchronous (pre-await) portion of this
  // function, so the mount effect below never sets state directly from
  // its own body — only the `finally` (reached after the await) does.
  // The "Refresh" button's onClick can set `loading` synchronously since
  // it isn't an effect.
  const fetchHistory = useCallback(async () => {
    try {
      setEntries(await runsHistory(40));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  function refresh() {
    setLoading(true);
    fetchHistory();
  }

  return (
    <div className="flex w-full flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 backdrop-blur">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <History className="size-4 text-cyan-300" />
          <h2 className="font-mono text-sm font-semibold uppercase tracking-widest text-slate-200">
            History of past runs
          </h2>
        </div>
        <button
          onClick={refresh}
          disabled={loading}
          className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-1.5 font-mono text-xs font-semibold text-slate-300 transition-colors hover:border-cyan-400/60 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RotateCw className={"size-3.5" + (loading ? " animate-spin" : "")} />
          Refresh
        </button>
      </div>

      {entries && entries.length > 0 ? (
        <div className="max-h-96 overflow-y-auto">
          <ul className="flex flex-col gap-1.5">
            {entries.map((e) => (
              <li
                key={e.run_id}
                className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-xs"
              >
                <div className="flex min-w-0 flex-col">
                  <span className="truncate text-slate-300">
                    {e.attack_label}
                  </span>
                  <span className="font-mono text-[10px] text-slate-500">
                    {e.config_label}
                  </span>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <span
                    className={
                      "rounded-full px-2 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider " +
                      (e.blocked
                        ? "bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/30"
                        : "bg-rose-500/10 text-rose-300 ring-1 ring-inset ring-rose-500/30")
                    }
                  >
                    {e.blocked ? "Blocked" : "Breached"}
                  </span>
                  <span className="font-mono text-[10px] text-slate-600">
                    {relativeTime(e.created_at)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : entries && entries.length === 0 ? (
        <p className="font-mono text-xs text-slate-600">
          No runs yet — fire the attack battery or run a comparison above.
        </p>
      ) : (
        <p className="font-mono text-xs text-slate-600">loading…</p>
      )}
    </div>
  );
}
