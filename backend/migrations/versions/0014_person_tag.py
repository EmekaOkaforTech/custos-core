"""Create person_tag table.

Revision ID: 0014_person_tag
Revises: 0013_person_notes
Create Date: 2026-01-30

Epic 32: Person Profile Enrichment - Story 32.3
Creates person_tag table for lightweight, user-defined tags on people.
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_person_tag"
down_revision = "0013_person_notes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_tag",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("person_id", sa.String(), nullable=False),
        sa.Column("tag", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["person_id"], ["person.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("person_id", "tag", name="uq_person_tag"),
    )
    op.create_index("ix_person_tag_person_id", "person_tag", ["person_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_person_tag_person_id", table_name="person_tag")
    op.drop_table("person_tag")
