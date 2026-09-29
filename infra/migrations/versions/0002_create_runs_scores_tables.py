"""create runs and scores tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-29

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("task_id", sa.String, nullable=False),
        sa.Column("llm_name", sa.String, nullable=False),
        sa.Column("defense_config", sa.String, nullable=False),
        sa.Column(
            "attack_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attacks.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String, nullable=False, server_default="pending"),
        sa.Column("final_answer", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "scores",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("run_id", sa.String, sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("utility", sa.Boolean, nullable=False),
        sa.Column("asr", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("scores")
    op.drop_table("runs")
