"""Celery app for async batch eval runs (build order step 6).

Broker/backend default to local Docker Redis so development doesn't
require Upstash to be provisioned. Set CELERY_BROKER_URL /
CELERY_RESULT_BACKEND to point at a real instance instead.

Three queues, per the root CLAUDE.md tech stack ("separate task queues:
attack_generation, task_execution, scoring — so a slow LLM call in one
stage doesn't block another"):
- attack_generation: the adaptive loop's retrieve+mutate step
- task_execution: running the Target Agent graph
- scoring: computing Utility/ASR from a completed run

Task results themselves aren't the source of truth — Postgres
(`runs`/`scores`) is. The Celery result backend only needs to answer
"did this task finish," so results expire quickly.
"""

from __future__ import annotations

import os

from celery import Celery

DEFAULT_BROKER_URL = "redis://localhost:6379/0"


def broker_url() -> str:
    return os.environ.get("CELERY_BROKER_URL", DEFAULT_BROKER_URL)


def result_backend_url() -> str:
    return os.environ.get("CELERY_RESULT_BACKEND", broker_url())


app = Celery(
    "canary", broker=broker_url(), backend=result_backend_url(), include=["api.tasks"]
)

app.conf.update(
    task_routes={
        "api.tasks.generate_attack_task": {"queue": "attack_generation"},
        "api.tasks.execute_task": {"queue": "task_execution"},
        "api.tasks.score_task": {"queue": "scoring"},
    },
    result_expires=3600,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)
