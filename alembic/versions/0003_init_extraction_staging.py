"""init: extracted_entity + extracted_relation + audit_log

Revision ID: 0003_init_extraction_staging
Revises: 0002_init_ontology_schema
Create Date: 2026-05-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0003_init_extraction_staging"
down_revision: Union[str, None] = "0002_init_ontology_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "extracted_entity",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("normalized_name", sa.String(length=200), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0"),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="FAKE"),
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("merged_into_id", sa.Uuid(), nullable=True),
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
            ["document_id"], ["document.id"], ondelete="CASCADE", name="fk_ee_document"
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunk.id"], ondelete="CASCADE", name="fk_ee_chunk"
        ),
        sa.ForeignKeyConstraint(
            ["merged_into_id"], ["extracted_entity.id"], ondelete="SET NULL", name="fk_ee_merged_into"
        ),
        sa.CheckConstraint(
            "review_status IN ('PENDING','APPROVED','REJECTED','MODIFIED','MERGED')",
            name="ck_extracted_entity_review_status",
        ),
        sa.CheckConstraint(
            "source IN ('LLM','FAKE','MANUAL')", name="ck_extracted_entity_source"
        ),
    )
    op.create_index("ix_ee_document", "extracted_entity", ["document_id"])
    op.create_index("ix_ee_chunk", "extracted_entity", ["chunk_id"])
    op.create_index("ix_ee_entity_type", "extracted_entity", ["entity_type"])
    op.create_index("ix_ee_normalized", "extracted_entity", ["normalized_name"])
    op.create_index("ix_ee_status", "extracted_entity", ["review_status"])

    op.create_table(
        "extracted_relation",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(), nullable=True),
        sa.Column("source_entity_name", sa.String(length=200), nullable=False),
        sa.Column("source_entity_type", sa.String(length=100), nullable=False),
        sa.Column("relation_type", sa.String(length=100), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(), nullable=True),
        sa.Column("target_entity_name", sa.String(length=200), nullable=False),
        sa.Column("target_entity_type", sa.String(length=100), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False, server_default="0"),
        sa.Column("evidence_text", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="FAKE"),
        sa.Column(
            "review_status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
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
            ["document_id"], ["document.id"], ondelete="CASCADE", name="fk_er_document"
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunk.id"], ondelete="CASCADE", name="fk_er_chunk"
        ),
        sa.ForeignKeyConstraint(
            ["source_entity_id"],
            ["extracted_entity.id"],
            ondelete="SET NULL",
            name="fk_er_source_entity",
        ),
        sa.ForeignKeyConstraint(
            ["target_entity_id"],
            ["extracted_entity.id"],
            ondelete="SET NULL",
            name="fk_er_target_entity",
        ),
        sa.CheckConstraint(
            "review_status IN ('PENDING','APPROVED','REJECTED','MODIFIED','MERGED')",
            name="ck_extracted_relation_review_status",
        ),
        sa.CheckConstraint(
            "source IN ('LLM','FAKE','MANUAL')", name="ck_extracted_relation_source"
        ),
    )
    op.create_index("ix_er_document", "extracted_relation", ["document_id"])
    op.create_index("ix_er_chunk", "extracted_relation", ["chunk_id"])
    op.create_index("ix_er_relation_type", "extracted_relation", ["relation_type"])
    op.create_index("ix_er_status", "extracted_relation", ["review_status"])
    op.create_index("ix_er_source_eid", "extracted_relation", ["source_entity_id"])
    op.create_index("ix_er_target_eid", "extracted_relation", ["target_entity_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor", sa.String(length=100), nullable=True),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("chunk_id", sa.Uuid(), nullable=True),
        sa.Column("before_json", JSONB, nullable=True),
        sa.Column("after_json", JSONB, nullable=True),
        sa.Column("metadata_json", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_action", "audit_log", ["action"])
    op.create_index("ix_audit_target_type", "audit_log", ["target_type"])
    op.create_index("ix_audit_target_id", "audit_log", ["target_id"])
    op.create_index("ix_audit_document", "audit_log", ["document_id"])
    op.create_index("ix_audit_chunk", "audit_log", ["chunk_id"])
    op.create_index("ix_audit_created_at", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_created_at", table_name="audit_log")
    op.drop_index("ix_audit_chunk", table_name="audit_log")
    op.drop_index("ix_audit_document", table_name="audit_log")
    op.drop_index("ix_audit_target_id", table_name="audit_log")
    op.drop_index("ix_audit_target_type", table_name="audit_log")
    op.drop_index("ix_audit_action", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_er_target_eid", table_name="extracted_relation")
    op.drop_index("ix_er_source_eid", table_name="extracted_relation")
    op.drop_index("ix_er_status", table_name="extracted_relation")
    op.drop_index("ix_er_relation_type", table_name="extracted_relation")
    op.drop_index("ix_er_chunk", table_name="extracted_relation")
    op.drop_index("ix_er_document", table_name="extracted_relation")
    op.drop_table("extracted_relation")

    op.drop_index("ix_ee_status", table_name="extracted_entity")
    op.drop_index("ix_ee_normalized", table_name="extracted_entity")
    op.drop_index("ix_ee_entity_type", table_name="extracted_entity")
    op.drop_index("ix_ee_chunk", table_name="extracted_entity")
    op.drop_index("ix_ee_document", table_name="extracted_entity")
    op.drop_table("extracted_entity")
