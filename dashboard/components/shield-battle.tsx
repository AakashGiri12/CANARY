"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Bot, Bug, Shield, ShieldOff, Zap } from "lucide-react";
import {
  type AttackOut,
  type ConfigOut,
  type HitOut,
  listConfigs,
  listStaticAttacks,
  runAdaptive,
  runStatic,
} from "@/lib/api";

type Step = {
  label: string;
  blocked: boolean;
  utility: boolean;
  payload?: string | null;
};

const MAX_CRACKS = 4;
const HIT_INTERVAL_MS = 1100;

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function CrackOverlay({ count }: { count: number }) {
  const paths = [
    "M50 8 L46 40 L58 46",
    "M50 8 L60 35 L48 52",
    "M20 50 L45 48 L40 70",
    "M80 45 L58 50 L66 75",
  ];
  return (
    <svg viewBox="0 0 100 100" className="absolute inset-0 h-full w-full">
      {paths.slice(0, count).map((d, i) => (
        <motion.path
          key={i}
          d={d}
          stroke="#fb7185"
          strokeWidth={2.5}
          fill="none"
          strokeLinecap="round"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 0.9 }}
          transition={{ duration: 0.3 }}
          style={{ filter: "drop-shadow(0 0 3px #fb7185)" }}
        />
      ))}
    </svg>
  );
}

function Fragments({ show }: { show: boolean }) {
  const pieces = Array.from({ length: 10 });
  return (
    <AnimatePresence>
      {show && (
        <>
          {pieces.map((_, i) => {
            const angle = (i / pieces.length) * Math.PI * 2;
            return (
              <motion.span
                key={i}
                className="absolute left-1/2 top-1/2 size-2 rounded-[2px] bg-rose-400"
                style={{ boxShadow: "0 0 8px rgba(251,113,133,0.9)" }}
                initial={{ x: 0, y: 0, opacity: 1, rotate: 0 }}
                animate={{
                  x: Math.cos(angle) * 70,
                  y: Math.sin(angle) * 70 + 30,
                  opacity: 0,
                  rotate: 220,
                }}
                transition={{ duration: 0.8, ease: "easeOut" }}
              />
            );
          })}
        </>
      )}
    </AnimatePresence>
  );
}

function Battlefield({
  active,
  shieldBroken,
  crackCount,
  justShattered,
}: {
  active: Step | null;
  shieldBroken: boolean;
  crackCount: number;
  justShattered: boolean;
}) {
  const breached = active ? !active.blocked : false;
  const danger = shieldBroken || (active && breached);

  return (
    <div
      className="relative flex h-48 items-center justify-between overflow-hidden rounded-2xl border px-12 backdrop-blur transition-colors duration-500"
      style={{
        borderColor: danger ? "rgba(251,113,133,0.4)" : "rgba(52,211,153,0.25)",
        background:
          "linear-gradient(180deg, rgba(15,23,42,0.9), rgba(2,6,23,0.9))",
        boxShadow: danger
          ? "0 0 60px -15px rgba(251,113,133,0.35) inset"
          : "0 0 60px -15px rgba(16,185,129,0.25) inset",
      }}
    >
      <div className="flex flex-col items-center gap-2 text-rose-300">
        <motion.div
          animate={active ? { x: [0, 6, -2, 0] } : {}}
          transition={{ duration: 0.3 }}
        >
          <Bug className="size-10 drop-shadow-[0_0_8px_rgba(251,113,133,0.6)]" />
        </motion.div>
        <span className="font-mono text-[11px] uppercase tracking-widest text-slate-500">
          Attacker
        </span>
      </div>

      <div className="relative flex flex-col items-center gap-2">
        <div className="relative flex size-20 items-center justify-center">
          {!shieldBroken && (
            <motion.div
              className="absolute inset-0 rounded-full"
              animate={{
                boxShadow: active
                  ? [
                      "0 0 0px rgba(16,185,129,0.0)",
                      "0 0 30px rgba(16,185,129,0.6)",
                      "0 0 0px rgba(16,185,129,0.0)",
                    ]
                  : "0 0 16px rgba(16,185,129,0.25)",
              }}
              transition={{ duration: 0.5 }}
            />
          )}
          {shieldBroken ? (
            <ShieldOff className="size-16 text-slate-600" />
          ) : (
            <motion.div
              animate={
                active
                  ? breached
                    ? { x: [0, -5, 5, -5, 0] }
                    : { x: [0, -7, 7, -3, 0], scale: [1, 0.9, 1] }
                  : {}
              }
              transition={{ duration: 0.35 }}
              className="relative"
            >
              <Shield
                className="size-16 text-emerald-400"
                style={{ filter: "drop-shadow(0 0 10px rgba(16,185,129,0.6))" }}
              />
              <CrackOverlay count={Math.min(crackCount, MAX_CRACKS)} />
            </motion.div>
          )}
          <Fragments show={justShattered} />
        </div>
        <span className="font-mono text-[11px] uppercase tracking-widest text-slate-500">
          {shieldBroken ? "Defense breached" : "Defense"}
        </span>

        <AnimatePresence>
          {active && (
            <motion.span
              key={active.label}
              initial={{ opacity: 0, x: -170, y: -6 }}
              animate={{ opacity: 1, x: breached && !shieldBroken ? 90 : 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="absolute top-1/2 -translate-y-1/2"
            >
              <Zap
                className={
                  breached
                    ? "size-6 text-rose-400"
                    : "size-6 text-amber-300"
                }
                style={{
                  filter: `drop-shadow(0 0 6px ${breached ? "#fb7185" : "#fcd34d"})`,
                }}
              />
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      <div className="flex flex-col items-center gap-2">
        <motion.div
          animate={
            active && breached && shieldBroken ? { x: [0, -6, 6, -6, 0] } : {}
          }
          transition={{ duration: 0.4 }}
        >
          <Bot
            className={
              "size-10 transition-colors duration-300 " +
              (active && breached && shieldBroken
                ? "text-rose-400 drop-shadow-[0_0_10px_rgba(251,113,133,0.7)]"
                : "text-cyan-300 drop-shadow-[0_0_8px_rgba(103,232,249,0.5)]")
            }
          />
        </motion.div>
        <span className="font-mono text-[11px] uppercase tracking-widest text-slate-500">
          Target Agent
        </span>
      </div>
    </div>
  );
}

function ResultLog({ steps }: { steps: Step[] }) {
  if (steps.length === 0) return null;
  return (
    <ul className="flex flex-col gap-2">
      {steps.map((s, i) => (
        <motion.li
          key={`${s.label}-${i}`}
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex flex-col gap-1.5 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-2.5 text-sm backdrop-blur"
        >
          <div className="flex items-center justify-between">
            <span className="text-slate-300">{s.label}</span>
            <span
              className={
                "rounded-full px-2.5 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider " +
                (s.blocked
                  ? "bg-emerald-500/10 text-emerald-300 ring-1 ring-inset ring-emerald-500/30"
                  : "bg-rose-500/10 text-rose-300 ring-1 ring-inset ring-rose-500/30")
              }
            >
              {s.blocked ? "Blocked" : "Breached"}
            </span>
          </div>
          {s.payload && (
            <p className="truncate font-mono text-[11px] text-slate-500">
              {s.payload}
            </p>
          )}
        </motion.li>
      ))}
    </ul>
  );
}

function StatTile({
  label,
  value,
  good,
}: {
  label: string;
  value: number;
  good: "low-is-good" | "high-is-good";
}) {
  const pct = value * 100;
  const isGood = good === "low-is-good" ? pct <= 20 : pct >= 80;
  const isBad = good === "low-is-good" ? pct > 50 : pct < 50;
  const color = isGood ? "text-emerald-300" : isBad ? "text-rose-300" : "text-amber-300";
  return (
    <div className="flex flex-1 flex-col items-center gap-1 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 backdrop-blur">
      <span className={`font-mono text-2xl font-bold ${color}`}>
        {pct.toFixed(0)}%
      </span>
      <span className="font-mono text-[11px] uppercase tracking-widest text-slate-500">
        {label}
      </span>
    </div>
  );
}

export function ShieldBattle() {
  const [configs, setConfigs] = useState<ConfigOut[]>([]);
  const [attacks, setAttacks] = useState<AttackOut[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string | null>(null);

  const [active, setActive] = useState<Step | null>(null);
  const [shieldBroken, setShieldBroken] = useState(false);
  const [crackCount, setCrackCount] = useState(0);
  const [justShattered, setJustShattered] = useState(false);
  const [steps, setSteps] = useState<Step[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [summary, setSummary] = useState<{ asr: number; utility: number } | null>(
    null
  );
  const runToken = useRef(0);

  useEffect(() => {
    listConfigs().then((cs) => {
      setConfigs(cs);
      setSelectedConfig((prev) => prev ?? cs[0]?.key ?? null);
    });
    listStaticAttacks().then(setAttacks);
  }, []);

  async function playSequence(hits: Step[]) {
    const token = ++runToken.current;
    setShieldBroken(false);
    setCrackCount(0);
    setSteps([]);
    setActive(null);

    for (const hit of hits) {
      if (runToken.current !== token) return;
      setActive(hit);
      await sleep(HIT_INTERVAL_MS * 0.4);

      if (!hit.blocked) {
        setShieldBroken((wasBroken) => {
          if (!wasBroken) {
            setJustShattered(true);
            setTimeout(() => setJustShattered(false), 800);
          }
          return true;
        });
      } else {
        setCrackCount((c) => Math.min(c + 1, MAX_CRACKS));
      }

      await sleep(HIT_INTERVAL_MS * 0.6);
      setSteps((prev) => [...prev, hit]);
    }
    setActive(null);
  }

  async function fireStaticBattery() {
    if (!selectedConfig || isRunning) return;
    setIsRunning(true);
    setSummary(null);
    try {
      const result = await runStatic(selectedConfig);
      const hits: Step[] = result.hits
        .filter((h) => h.attack_id !== null)
        .map((h: HitOut) => ({
          label: h.attack_label,
          blocked: h.blocked,
          utility: h.utility,
          payload: h.payload_preview,
        }));
      await playSequence(hits);
      setSummary({ asr: result.asr_rate, utility: result.utility_rate });
    } finally {
      setIsRunning(false);
    }
  }

  async function fireAdaptiveLoop() {
    if (!selectedConfig || isRunning) return;
    setIsRunning(true);
    setSummary(null);
    try {
      const result = await runAdaptive(selectedConfig, 5);
      const hits: Step[] = result.generations.map((g) => ({
        label: `Mutation #${g.generation} (framing ${g.framing_index})`,
        blocked: g.blocked,
        utility: g.utility,
      }));
      await playSequence(hits);
      const breaches = hits.filter((h) => !h.blocked).length;
      setSummary({
        asr: breaches / hits.length,
        utility: hits.filter((h) => h.utility).length / hits.length,
      });
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-6 xl:max-w-none">
      <Battlefield
        active={active}
        shieldBroken={shieldBroken}
        crackCount={crackCount}
        justShattered={justShattered}
      />

      <div className="flex flex-wrap items-center justify-center gap-2">
        {configs.map((c) => (
          <button
            key={c.key}
            onClick={() => setSelectedConfig(c.key)}
            disabled={isRunning}
            className={
              "rounded-full border px-3.5 py-1.5 font-mono text-xs transition-all disabled:cursor-not-allowed disabled:opacity-50 " +
              (selectedConfig === c.key
                ? "border-emerald-400/60 bg-emerald-500/15 text-emerald-300 shadow-[0_0_20px_-5px_rgba(16,185,129,0.6)]"
                : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700 hover:text-slate-200")
            }
          >
            {c.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap justify-center gap-3">
        <button
          onClick={fireStaticBattery}
          disabled={isRunning || !selectedConfig}
          className="rounded-lg bg-gradient-to-r from-emerald-400 to-cyan-400 px-4 py-2 font-mono text-sm font-semibold text-slate-950 shadow-[0_0_25px_-8px_rgba(16,185,129,0.8)] transition-transform hover:scale-[1.02] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
        >
          Fire static attack battery
        </button>
        <button
          onClick={fireAdaptiveLoop}
          disabled={isRunning || !selectedConfig}
          className="rounded-lg border border-slate-700 bg-slate-900/60 px-4 py-2 font-mono text-sm font-semibold text-slate-200 transition-colors hover:border-cyan-400/60 hover:text-cyan-300 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Run adaptive attacker (5 gens)
        </button>
      </div>

      {summary && (
        <div className="flex gap-3">
          <StatTile label="Attack Success Rate" value={summary.asr} good="low-is-good" />
          <StatTile label="Task Utility" value={summary.utility} good="high-is-good" />
        </div>
      )}

      <ResultLog steps={steps} />

      {attacks.length === 0 && (
        <p className="font-mono text-xs text-slate-600">
          connecting to {process.env.NEXT_PUBLIC_API_URL}…
        </p>
      )}
    </div>
  );
}
