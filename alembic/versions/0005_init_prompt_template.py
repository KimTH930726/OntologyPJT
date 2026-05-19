"""init: prompt_template + prompt_version

Revision ID: 0005_init_prompt_template
Revises: 0004_init_graph_sync_log
Create Date: 2026-05-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_init_prompt_template"
down_revision: Union[str, None] = "0004_init_graph_sync_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_template",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("name", name="uq_prompt_template_name"),
    )

    op.create_table(
        "prompt_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("template_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["prompt_template.id"],
            ondelete="CASCADE",
            name="fk_pv_template",
        ),
        sa.UniqueConstraint(
            "template_id", "version", name="uq_prompt_version_template_ver"
        ),
    )
    op.create_index("ix_pv_template", "prompt_version", ["template_id"])
    # Partial unique: enforce at most one active version per template.
    op.create_index(
        "uq_prompt_version_active_per_template",
        "prompt_version",
        ["template_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    op.drop_index("uq_prompt_version_active_per_template", table_name="prompt_version")
    op.drop_index("ix_pv_template", table_name="prompt_version")
    op.drop_table("prompt_version")
    op.drop_table("prompt_template")
