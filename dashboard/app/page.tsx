import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-background px-6 text-center">
      <div className="flex flex-col gap-2">
        <h1 className="text-4xl font-semibold tracking-tight">CANARY</h1>
        <p className="max-w-md text-muted-foreground">
          Adversarial agent security dashboard. Eval run history and the
          Utility / Attack Success Rate Pareto frontier will appear here.
        </p>
      </div>
      <Button disabled>Runs coming soon</Button>
    </div>
  );
}
