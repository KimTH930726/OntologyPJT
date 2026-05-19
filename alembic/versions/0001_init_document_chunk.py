"""init: document + document_chunk

Revision ID: 0001_init_document_chunk
Revises:
Create Date: 2026-05-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_init_document_chunk"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=False, server_default="document"),
        sa.Column("version", sa.String(length=50), nullable=False, server_default="v1"),
        sa.Column("access_level", sa.String(length=50), nullable=False, server_default="internal"),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
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
        sa.UniqueConstraint("content_hash", name="uq_document_content_hash"),
    )
    op.create_index("ix_document_domain", "document", ["domain"])
    op.create_index("ix_document_created_at", "document", ["created_at"])

    op.create_table(
        "document_chunk",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "vector_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("qdrant_point_id", sa.String(length=64), nullable=True),
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
            ["document_id"], ["document.id"], ondelete="CASCADE", name="fk_chunk_document"
        ),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_chunk_document_index"),
        sa.CheckConstraint(
            "vector_status IN ('PENDING','INDEXED','FAILED')",
            name="ck_chunk_vector_status",
        ),
    )
    op.create_index("ix_chunk_document", "document_chunk", ["document_id"])
    op.create_index("ix_chunk_vector_status", "document_chunk", ["vector_status"])


def downgrade() -> None:
    op.drop_index("ix_chunk_vector_status", table_name="document_chunk")
    op.drop_index("ix_chunk_document", table_name="document_chunk")
    op.drop_table("document_chunk")
    op.drop_index("ix_document_created_at", table_name="document")
    op.drop_index("ix_document_domain", table_name="document")
    op.drop_table("document")
