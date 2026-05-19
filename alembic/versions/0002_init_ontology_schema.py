"""init: ontology_entity_type + ontology_relation_type

Revision ID: 0002_init_ontology_schema
Revises: 0001_init_document_chunk
Create Date: 2026-05-19

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_init_ontology_schema"
down_revision: Union[str, None] = "0001_init_document_chunk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ontology_entity_type",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint("name", name="uq_ontology_entity_type_name"),
    )

    op.create_table(
        "ontology_relation_type",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_entity_type", sa.String(length=100), nullable=False),
        sa.Column("relation_name", sa.String(length=100), nullable=False),
        sa.Column("target_entity_type", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint(
            "source_entity_type",
            "relation_name",
            "target_entity_type",
            name="uq_relation_signature",
        ),
    )
    op.create_index(
        "ix_ontology_relation_source", "ontology_relation_type", ["source_entity_type"]
    )
    op.create_index(
        "ix_ontology_relation_target", "ontology_relation_type", ["target_entity_type"]
    )
    op.create_index(
        "ix_ontology_relation_name", "ontology_relation_type", ["relation_name"]
    )


def downgrade() -> None:
    op.drop_index("ix_ontology_relation_name", table_name="ontology_relation_type")
    op.drop_index("ix_ontology_relation_target", table_name="ontology_relation_type")
    op.drop_index("ix_ontology_relation_source", table_name="ontology_relation_type")
    op.drop_table("ontology_relation_type")
    op.drop_table("ontology_entity_type")
