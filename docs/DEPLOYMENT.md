# Deploying CANARY's dashboard + API publicly

Three free services, in this order (each depends on the one before it).
None of this can be done by Claude Code — each step needs your own
account/login in that service's own UI. Code-side support (CORS, the
shared-token gate, `render.yaml`, env var wiring) is already in place.

## 1. Database — Neon (free Postgres + pgvector)

1. Sign up at neon.tech, create a project.
2. Copy the connection string it gives you (starts `postgresql://...`).
   Use the **pooled** connection string if offered one.
3. Run migrations against it from this repo:
   ```bash
   DATABASE_URL="<your neon connection string>" \
     .venv/bin/python3 -m alembic -c infra/alembic.ini upgrade head
   ```
   (Neon supports the `vector` extension the first migration creates —
   confirmed, not assumed.)

## 2. Backend API — Render (free web service)

1. Sign up at render.com, connect your GitHub account, give it access to
   the `CANARY` repo.
2. "New +" → "Blueprint" → select this repo. Render reads `render.yaml`
   at the repo root and proposes the `canary-api` service automatically.
3. Before/after creating it, set these env vars in Render's dashboard
   (Settings → Environment):
   - `DEEPSEEK_API_KEY` — your real key
   - `DATABASE_URL` — the Neon connection string from step 1
   - `CANARY_API_TOKEN` — make up a random string (e.g. `openssl rand
     -hex 16`) — this is the shared secret the dashboard will send
   - `CORS_ORIGINS` — leave blank for now, come back and set it after
     step 3 gives you the Vercel URL (needs to be
     `http://localhost:3000,https://<your-vercel-url>`)
4. Deploy. Note the service's URL (`https://canary-api-xxxx.onrender.com`).
5. **Free-tier behavior**: spins down after ~15 min idle; the first
   request after that takes 30-60s to wake up. Hit
   `https://<your-render-url>/api/health` a few minutes before a live
   demo so it's already warm.

## 3. Frontend — Vercel

1. Sign up at vercel.com, "Add New" → "Project" → import the `CANARY`
   repo.
2. **Root Directory**: set to `dashboard` (this is a monorepo — Vercel
   needs to know the Next.js app isn't at the repo root).
3. Environment variables (Project Settings → Environment Variables):
   - `NEXT_PUBLIC_API_URL` — the Render URL from step 2
   - `NEXT_PUBLIC_API_TOKEN` — the same `CANARY_API_TOKEN` value from
     step 2 (must match exactly)
4. Deploy. Note the resulting URL (`https://canary-xxxx.vercel.app`).
5. Go back to Render and set `CORS_ORIGINS` to include this exact URL
   (comma-separated with `http://localhost:3000` if you still want local
   dev to keep working), then redeploy the Render service so the new
   env var takes effect.

## Verifying it actually works

```bash
curl https://<your-render-url>/api/health
# {"status":"ok"}

curl -H "X-API-Token: <your token>" https://<your-render-url>/api/configs
# should list the 6 configs, not a 401
```

Then open the Vercel URL in a browser and click through the demo.

## What the shared token does and doesn't do

`CANARY_API_TOKEN` / `NEXT_PUBLIC_API_TOKEN` is a basic deterrent, not
real authentication: `NEXT_PUBLIC_*` values are compiled into the
client-side JS bundle and are visible to anyone who opens browser dev
tools on the deployed site. It stops a leaked link from being casually
clicked by strangers; it does not stop someone who specifically goes
looking for the token. Don't treat this as a reason to stop worrying
about the link leaking — take the Render/Vercel deployments down after
you're done presenting if you want a hard guarantee against further
cost.
