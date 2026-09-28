# api

FastAPI service — the backend that ties everything together.

Exposes endpoints for triggering eval runs, querying run/attack/score history
(the `runs`, `attacks`, `scores` relational tables), and streaming live attack
demos to the Next.js dashboard over SSE/WebSocket. Dispatches long-running eval
batches to Celery workers rather than running them in-request.

Runs on the Oracle Always Free VM in production; Postgres is Neon/Supabase and
Redis is Upstash, both free tier — this service itself talks to them over the
network rather than hosting them.
