"""Add commitment_relevant_by to ingestion_job

Revision ID: 0009_commitment_relevant_by
Revises: 0008_dedupe_keys
Create Date: 2026-01-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_commitment_relevant_by"
down_revision = "0008_dedupe_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_job", sa.Column("commitment_relevant_by", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("ingestion_job", "commitment_relevant_by")
