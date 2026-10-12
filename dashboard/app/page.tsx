import { ClassifierDefense } from "@/components/classifier-defense";
import { ConfigComparison } from "@/components/config-comparison";
import { ShieldBattle } from "@/components/shield-battle";

export default function Home() {
  return (
    <div className="relative flex min-h-screen flex-col items-center gap-10 overflow-hidden bg-slate-950 px-6 py-16 text-center">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(148,163,184,0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(148,163,184,0.08) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />
      <div
        className="pointer-events-none absolute left-1/2 top-[-10%] h-[500px] w-[800px] -translate-x-1/2 rounded-full opacity-25 blur-[120px]"
        style={{
          background:
            "radial-gradient(circle, rgba(16,185,129,0.5), rgba(6,182,212,0.3) 40%, transparent 70%)",
        }}
      />

      <div className="relative z-10 flex flex-col gap-3">
        <h1 className="bg-gradient-to-r from-emerald-300 via-cyan-300 to-emerald-300 bg-clip-text text-5xl font-bold tracking-tight text-transparent drop-shadow-[0_0_30px_rgba(16,185,129,0.35)]">
          CANARY
        </h1>
        <p className="max-w-lg text-sm text-slate-400">
          Pick a defense config, then fire the static attack battery or the
          adaptive attacker and watch each attempt hit the shield — live
          against the real Target Agent, not a replay.
        </p>
      </div>

      <div className="relative z-10 grid w-full max-w-7xl grid-cols-1 items-start gap-8 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <ShieldBattle />
        <ConfigComparison />
      </div>

      <div className="relative z-10 w-full max-w-7xl">
        <ClassifierDefense />
      </div>
    </div>
  );
}
