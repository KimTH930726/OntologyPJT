"""init: graph_sync_log

Revision ID: 0004_init_graph_sync_log
Revises: 0003_init_extraction_staging
Create Date: 2026-05-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_init_graph_sync_log"
down_revision: Union[str, None] = "0003_init_extraction_staging"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "graph_sync_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("sync_status", sa.String(length=20), nullable=False),
        sa.Column("neo4j_node_id", sa.String(length=100), nullable=True),
        sa.Column("neo4j_relation_id", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "target_type IN ('ENTITY','RELATION')", name="ck_gsl_target_type"
        ),
        sa.CheckConstraint(
            "sync_status IN ('SUCCESS','FAILED','SKIPPED')", name="ck_gsl_sync_status"
        ),
    )
    op.create_index("ix_gsl_target_type", "graph_sync_log", ["target_type"])
    op.create_index("ix_gsl_target_id", "graph_sync_log", ["target_id"])
    op.create_index("ix_gsl_sync_status", "graph_sync_log", ["sync_status"])
    op.create_index("ix_gsl_created_at", "graph_sync_log", ["created_at"])
    op.create_index(
        "ix_gsl_target_status",
        "graph_sync_log",
        ["target_type", "target_id", "sync_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_gsl_target_status", table_name="graph_sync_log")
    op.drop_index("ix_gsl_created_at", table_name="graph_sync_log")
    op.drop_index("ix_gsl_sync_status", table_name="graph_sync_log")
    op.drop_index("ix_gsl_target_id", table_name="graph_sync_log")
    op.drop_index("ix_gsl_target_type", table_name="graph_sync_log")
    op.drop_table("graph_sync_log")
