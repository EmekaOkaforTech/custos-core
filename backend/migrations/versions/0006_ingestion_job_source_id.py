"""Add source_id to ingestion_job

Revision ID: 0006_ingestion_job_source_id
Revises: 0005_indexes
Create Date: 2026-01-23
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_ingestion_job_source_id"
down_revision = "0005_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_job", sa.Column("source_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingestion_job", "source_id")
