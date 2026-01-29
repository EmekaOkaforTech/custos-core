"""Add people_ids to source_record

Revision ID: 0011_source_people_ids
Revises: 0010_index_in_memory
Create Date: 2026-01-29 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_source_people_ids"
down_revision = "0010_index_in_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("source_record", sa.Column("people_ids", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("source_record", "people_ids")
