"""Add role column to person table.

Revision ID: 0012_person_role
Revises: 0011_source_people_ids
Create Date: 2026-01-30

Epic 32: Person Profile Enrichment - Story 32.2
Adds editable role field to Person (e.g., "client", "family", "colleague").
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_person_role"
down_revision = "0011_source_people_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("person", sa.Column("role", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("person", "role")
