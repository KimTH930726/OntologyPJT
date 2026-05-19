"""init: ai_query_log

Revision ID: 0006_init_ai_query_log
Revises: 0005_init_prompt_template
Create Date: 2026-05-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0006_init_ai_query_log"
down_revision: Union[str, None] = "0005_init_prompt_template"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_query_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("detected_entities_json", JSONB, nullable=True),
        sa.Column("graph_context_json", JSONB, nullable=True),
        sa.Column("retrieved_chunks_json", JSONB, nullable=True),
        sa.Column("final_prompt", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("model_provider", sa.String(length=50), nullable=True),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("token_estimate", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_aql_created_at", "ai_query_log", ["created_at"])
    op.create_index("ix_aql_model_provider", "ai_query_log", ["model_provider"])


def downgrade() -> None:
    op.drop_index("ix_aql_model_provider", table_name="ai_query_log")
    op.drop_index("ix_aql_created_at", table_name="ai_query_log")
    op.drop_table("ai_query_log")
