"""add indexes

Revision ID: 0005_indexes
Revises: 0004_meeting_source
Create Date: 2026-01-18
"""

from alembic import op

revision = "0005_indexes"
down_revision = "0004_meeting_source"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_meeting_starts_at", "meeting", ["starts_at"], unique=False)
    op.create_index("ix_source_record_meeting_id", "source_record", ["meeting_id"], unique=False)
    op.create_index("ix_commitment_source_id", "commitment", ["source_id"], unique=False)
    op.create_index("ix_risk_flag_source_id", "risk_flag", ["source_id"], unique=False)
    op.create_index("ix_meeting_participant_meeting_id", "meeting_participant", ["meeting_id"], unique=False)
    op.create_index("ix_meeting_participant_person_id", "meeting_participant", ["person_id"], unique=False)


def downgrade():
    op.drop_index("ix_meeting_participant_person_id", table_name="meeting_participant")
    op.drop_index("ix_meeting_participant_meeting_id", table_name="meeting_participant")
    op.drop_index("ix_risk_flag_source_id", table_name="risk_flag")
    op.drop_index("ix_commitment_source_id", table_name="commitment")
    op.drop_index("ix_source_record_meeting_id", table_name="source_record")
    op.drop_index("ix_meeting_starts_at", table_name="meeting")
