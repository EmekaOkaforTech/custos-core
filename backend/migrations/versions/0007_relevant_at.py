"""Add relevant_at to ingestion_job and source_record

Revision ID: 0007_relevant_at
Revises: 0006_ingestion_job_source_id
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_relevant_at"
down_revision = "0006_ingestion_job_source_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_job", sa.Column("relevant_at", sa.DateTime(), nullable=True))
    op.add_column("source_record", sa.Column("relevant_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("source_record", "relevant_at")
    op.drop_column("ingestion_job", "relevant_at")
