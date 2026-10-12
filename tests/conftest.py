import os
import uuid

import pytest
from sqlalchemy import create_engine, text

# Found live: pytest's own fixture rows (exec-*, score-*, test-model-*)
# were showing up as real entries in the dashboard's "history of past
# runs" feature, because tests and the live API were both pointed at the
# same local Postgres database by default. Every test that touches
# Postgres (attack_engine.db / api.tasks) must run against a dedicated
# canary_test database instead — never the one the live demo reads from.
TEST_DATABASE_URL = "postgresql+psycopg2://canary:canary@localhost:5432/canary_test"
_ADMIN_DATABASE_URL = "postgresql+psycopg2://canary:canary@localhost:5432/canary"


def _ensure_test_database() -> None:
    admin_engine = create_engine(
        _ADMIN_DATABASE_URL, isolation_level="AUTOCOMMIT", future=True
    )
    try:
        with admin_engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = 'canary_test'")
            ).first()
            if not exists:
                conn.execute(text("CREATE DATABASE canary_test"))
    finally:
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _isolated_test_database():
    """Points DATABASE_URL at canary_test for the whole test session,
    creating the database and its schema (pgvector extension + all
    tables) if they don't exist yet. Session-scoped + autouse: every test
    benefits even if it doesn't request this fixture by name, and it only
    pays the setup cost once per test run."""
    _ensure_test_database()
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    from attack_engine.db import Base, get_engine, reset_engine_cache

    reset_engine_cache()
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(engine)

    yield

    reset_engine_cache()
    os.environ.pop("DATABASE_URL", None)


@pytest.fixture
def unique_model_defense():
    """A unique (target_model, defense_config) pair per test, so
    attack_memory rows written by one test don't leak into another's
    retrieval query."""
    suffix = uuid.uuid4().hex[:8]
    return f"test-model-{suffix}", f"test-defense-{suffix}"
