"""Add capture visibility and owner fields

Revision ID: 0035_capture_visibility
Revises: 0034_user_accounts
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0035_capture_visibility"
down_revision = "0034_user_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingestion_job", sa.Column("owner_id", sa.String(), nullable=True))
    op.add_column("ingestion_job", sa.Column("visibility", sa.String(), nullable=False, server_default="personal"))
    op.add_column("source_record", sa.Column("owner_id", sa.String(), nullable=True))
    op.add_column("source_record", sa.Column("visibility", sa.String(), nullable=False, server_default="personal"))


def downgrade() -> None:
    op.drop_column("source_record", "visibility")
    op.drop_column("source_record", "owner_id")
    op.drop_column("ingestion_job", "visibility")
    op.drop_column("ingestion_job", "owner_id")
