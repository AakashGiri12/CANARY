"""Read/write access to attack_memory: the retrieval corpus for the
adaptive Attack Engine loop (build order step 4).

Retrieval flow (per the root CLAUDE.md): before generating a new
mutation, embed the current context, pull top-k similar past attempts
filtered by target_model/defense_config, feed them into the mutation
step, write the new result back after the run.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select

from attack_engine.db import Attack, AttackMemory, get_session
from attack_engine.embeddings import Embedder


@dataclass(frozen=True)
class RetrievedMemory:
    id: uuid.UUID
    attack_id: uuid.UUID | None
    payload_text: str
    target_model: str
    defense_config: str
    outcome: str
    asr_delta: float | None


def record_attack(
    *,
    name: str,
    target_key: str,
    payload_text: str,
    success_marker: str,
    generation: str = "seed",
    parent_attack_id: uuid.UUID | None = None,
) -> uuid.UUID:
    with get_session() as session:
        attack = Attack(
            name=name,
            target_key=target_key,
            payload_text=payload_text,
            success_marker=success_marker,
            generation=generation,
            parent_attack_id=parent_attack_id,
        )
        session.add(attack)
        session.commit()
        session.refresh(attack)
        return attack.id


def record_outcome(
    *,
    attack_id: uuid.UUID | None,
    payload_text: str,
    embedder: Embedder,
    target_model: str,
    defense_config: str,
    outcome: str,
    asr_delta: float | None = None,
) -> uuid.UUID:
    embedding = embedder.embed(payload_text)
    with get_session() as session:
        memory = AttackMemory(
            attack_id=attack_id,
            payload_text=payload_text,
            embedding=embedding,
            target_model=target_model,
            defense_config=defense_config,
            outcome=outcome,
            asr_delta=asr_delta,
        )
        session.add(memory)
        session.commit()
        session.refresh(memory)
        return memory.id


def get_or_create_attack_by_name(
    *,
    name: str,
    target_key: str,
    payload_text: str,
    success_marker: str,
    generation: str = "seed",
) -> uuid.UUID:
    """Idempotent: returns the existing row's id if one with this name
    already exists, else inserts a new one."""
    with get_session() as session:
        existing = session.scalars(select(Attack).where(Attack.name == name)).first()
        if existing is not None:
            return existing.id
        attack = Attack(
            name=name,
            target_key=target_key,
            payload_text=payload_text,
            success_marker=success_marker,
            generation=generation,
        )
        session.add(attack)
        session.commit()
        session.refresh(attack)
        return attack.id


def seed_static_attacks() -> dict[str, uuid.UUID]:
    """Idempotently insert attack_engine.library.STATIC_ATTACKS into the
    `attacks` table (keyed by AttackSpec.id, stored as Attack.name), so
    static and adaptively-generated attacks share one table and `runs`
    rows can FK to either. Returns {AttackSpec.id (str) -> DB row UUID}.
    """
    from attack_engine.library import STATIC_ATTACKS

    return {
        attack.id: get_or_create_attack_by_name(
            name=attack.id,
            target_key=attack.target_key,
            payload_text=attack.payload_text,
            success_marker=attack.success_marker,
            generation="seed",
        )
        for attack in STATIC_ATTACKS
    }


def clear_memory(*, target_model: str, defense_config: str) -> int:
    """Delete all attack_memory rows for a (target_model, defense_config)
    pair. Used by tests and demo entrypoints for reproducible runs."""
    with get_session() as session:
        stmt = select(AttackMemory).where(
            AttackMemory.target_model == target_model,
            AttackMemory.defense_config == defense_config,
        )
        rows = session.scalars(stmt).all()
        for row in rows:
            session.delete(row)
        session.commit()
        return len(rows)


def retrieve_similar(
    *,
    query_text: str,
    embedder: Embedder,
    target_model: str,
    defense_config: str,
    top_k: int = 5,
) -> list[RetrievedMemory]:
    query_embedding = embedder.embed(query_text)
    with get_session() as session:
        stmt = (
            select(AttackMemory)
            .where(AttackMemory.target_model == target_model)
            .where(AttackMemory.defense_config == defense_config)
            .order_by(AttackMemory.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        rows = session.scalars(stmt).all()
        return [
            RetrievedMemory(
                id=row.id,
                attack_id=row.attack_id,
                payload_text=row.payload_text,
                target_model=row.target_model,
                defense_config=row.defense_config,
                outcome=row.outcome,
                asr_delta=row.asr_delta,
            )
            for row in rows
        ]
