"""SQLAlchemy models + session for the whole project's shared Postgres:
`attacks` + `attack_memory` (pgvector semantic retrieval, build order
step 4) and `runs` + `scores` (structured lineage, build order step 6),
all in one database per the root CLAUDE.md ("Memory / Knowledge base" —
keeps metadata and embeddings joinable in one query, not a separate
vector DB). One shared module rather than splitting by which package
happens to use a table, since they're genuinely the same database.

Connects to local Docker Postgres by default (`infra/docker-compose.yml`)
so development doesn't require the cloud Postgres (Neon/Supabase) to be
provisioned. Set DATABASE_URL to point at a real instance instead.
"""

from __future__ import annotations

import os

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    create_engine,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql+psycopg2://canary:canary@localhost:5432/canary"
EMBEDDING_DIM = 384  # sentence-transformers/all-MiniLM-L6-v2


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


class Base(DeclarativeBase):
    pass


class Attack(Base):
    """One attack variant — a static seed or an adaptively mutated one."""

    __tablename__ = "attacks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)
    target_key = Column(String, nullable=False)
    payload_text = Column(Text, nullable=False)
    success_marker = Column(String, nullable=False)
    generation = Column(String, nullable=False, default="seed")  # "seed" | "gen-1" | "gen-2" | ...
    parent_attack_id = Column(UUID(as_uuid=True), ForeignKey("attacks.id"), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class AttackMemory(Base):
    """Outcome of running one attack against one (target_model,
    defense_config) pair — the retrieval corpus for the adaptive loop."""

    __tablename__ = "attack_memory"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    attack_id = Column(UUID(as_uuid=True), ForeignKey("attacks.id"), nullable=True)
    payload_text = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)
    target_model = Column(String, nullable=False)
    defense_config = Column(String, nullable=False)
    outcome = Column(String, nullable=False)  # 'success' | 'blocked' | 'partial'
    asr_delta = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=text("now()"), nullable=False
    )


class Run(Base):
    """One Target Agent execution: (llm_name, task_id, attack_id,
    defense_config). `id` is a deterministic string key (not a random
    UUID) so resubmitting the same batch after a crash naturally maps
    to the same row — that's what makes checkpointing/resumability
    possible: Celery tasks check for an existing 'completed' row before
    doing any work."""

    __tablename__ = "runs"

    id = Column(String, primary_key=True)
    task_id = Column(String, nullable=False)
    llm_name = Column(String, nullable=False)
    defense_config = Column(String, nullable=False)
    attack_id = Column(UUID(as_uuid=True), ForeignKey("attacks.id"), nullable=True)
    status = Column(String, nullable=False, server_default="pending")  # pending|running|completed|failed
    final_answer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class Score(Base):
    """Utility/ASR score for one completed Run."""

    __tablename__ = "scores"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id = Column(String, ForeignKey("runs.id"), nullable=False)
    utility = Column(Boolean, nullable=False)
    asr = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"), nullable=False)


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(database_url(), future=True)
    return _engine


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), future=True)
    return _SessionLocal()


def reset_engine_cache() -> None:
    """Test helper: drop cached engine/session so a changed DATABASE_URL
    (e.g. a test DB) takes effect on the next get_engine()/get_session()."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None
