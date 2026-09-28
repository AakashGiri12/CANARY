"""structlog configuration for the Target Agent.

Every model turn and tool call is logged as a structured JSON event so the
Eval Harness can reconstruct a run later without re-running it.
"""

from __future__ import annotations

import structlog


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_run_logger(run_id: str) -> structlog.BoundLogger:
    return structlog.get_logger().bind(run_id=run_id)
