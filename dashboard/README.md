# dashboard

Next.js + TypeScript frontend. Deployed to Vercel free tier.

Visualizes eval runs: the Utility/ASR Pareto frontier across defense configs,
live attack demos streamed from the FastAPI backend, and run/attack history.

Explicitly not Streamlit — this must be a real production frontend stack
(Next.js, Tailwind, shadcn/ui, Recharts/Tremor for charts) per the project's
hard constraints in the root CLAUDE.md.

## Getting started

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view it. Bootstrapped
with `create-next-app` (TypeScript, Tailwind, App Router); components come
from shadcn/ui.
