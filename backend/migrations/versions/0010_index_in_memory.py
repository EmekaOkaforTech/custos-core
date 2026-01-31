"""Add index_in_memory flag

Revision ID: 0010_index_in_memory
Revises: 0009_commitment_relevant_by
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0010_index_in_memory"
down_revision = "0009_commitment_relevant_by"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_job", sa.Column("index_in_memory", sa.Boolean(), nullable=True))
    op.add_column("source_record", sa.Column("index_in_memory", sa.Boolean(), nullable=True))
    op.execute("UPDATE ingestion_job SET index_in_memory = 1 WHERE capture_type = 'reflection'")
    op.execute("UPDATE ingestion_job SET index_in_memory = 0 WHERE index_in_memory IS NULL")
    op.execute("UPDATE source_record SET index_in_memory = 1 WHERE capture_type = 'reflection'")
    op.execute("UPDATE source_record SET index_in_memory = 0 WHERE index_in_memory IS NULL")


def downgrade() -> None:
    op.drop_column("source_record", "index_in_memory")
    op.drop_column("ingestion_job", "index_in_memory")
