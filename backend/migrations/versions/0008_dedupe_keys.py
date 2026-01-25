"""Add dedupe keys to ingestion_job and source_record

Revision ID: 0008_dedupe_keys
Revises: 0007_relevant_at
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0008_dedupe_keys"
down_revision = "0007_relevant_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_job", sa.Column("dedupe_key", sa.String(), nullable=True))
    op.create_index("ix_ingestion_job_dedupe_key", "ingestion_job", ["dedupe_key"], unique=True)
    op.add_column("source_record", sa.Column("dedupe_key", sa.String(), nullable=True))
    op.create_index("ix_source_record_dedupe_key", "source_record", ["dedupe_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_source_record_dedupe_key", table_name="source_record")
    op.drop_column("source_record", "dedupe_key")
    op.drop_index("ix_ingestion_job_dedupe_key", table_name="ingestion_job")
    op.drop_column("ingestion_job", "dedupe_key")
