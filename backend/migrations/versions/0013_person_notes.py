"""Add person notes support.

Revision ID: 0013_person_notes
Revises: 0012_person_role
Create Date: 2026-01-30

Epic 32: Person Profile Enrichment - Story 32.1
Adds person_id to source_record and ingestion_job tables to support
capturing notes directly to a person without requiring a meeting.
"""

from alembic import op
import sqlalchemy as sa

revision = "0013_person_notes"
down_revision = "0012_person_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add person_id column to source_record
    with op.batch_alter_table("source_record") as batch_op:
        batch_op.add_column(sa.Column("person_id", sa.String(), nullable=True))
        batch_op.alter_column("meeting_id", existing_type=sa.String(), nullable=True)
        batch_op.create_index("ix_source_record_person_id", ["person_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_source_record_person_id",
            "person",
            ["person_id"],
            ["id"],
        )

    # Add person_id column to ingestion_job
    with op.batch_alter_table("ingestion_job") as batch_op:
        batch_op.add_column(sa.Column("person_id", sa.String(), nullable=True))
        batch_op.alter_column("meeting_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    # Remove person_id from ingestion_job
    with op.batch_alter_table("ingestion_job") as batch_op:
        batch_op.alter_column("meeting_id", existing_type=sa.String(), nullable=False)
        batch_op.drop_column("person_id")

    # Remove person_id from source_record
    with op.batch_alter_table("source_record") as batch_op:
        batch_op.drop_constraint("fk_source_record_person_id", type_="foreignkey")
        batch_op.drop_index("ix_source_record_person_id")
        batch_op.alter_column("meeting_id", existing_type=sa.String(), nullable=False)
        batch_op.drop_column("person_id")
