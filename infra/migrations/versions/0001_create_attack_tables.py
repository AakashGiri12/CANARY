"""create attacks and attack_memory tables

Revision ID: 0001
Revises:
Create Date: 2026-09-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "attacks",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("target_key", sa.String, nullable=False),
        sa.Column("payload_text", sa.Text, nullable=False),
        sa.Column("success_marker", sa.String, nullable=False),
        sa.Column("generation", sa.String, nullable=False, server_default="seed"),
        sa.Column(
            "parent_attack_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attacks.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "attack_memory",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "attack_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attacks.id"),
            nullable=True,
        ),
        sa.Column("payload_text", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column("target_model", sa.String, nullable=False),
        sa.Column("defense_config", sa.String, nullable=False),
        sa.Column("outcome", sa.String, nullable=False),
        sa.Column("asr_delta", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.execute(
        "CREATE INDEX ON attack_memory USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("attack_memory")
    op.drop_table("attacks")
