"""add meeting participant

Revision ID: 0002_meeting_participant
Revises: 0001_initial
Create Date: 2026-01-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_meeting_participant"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "meeting_participant",
        sa.Column("meeting_id", sa.String(), sa.ForeignKey("meeting.id"), primary_key=True),
        sa.Column("person_id", sa.String(), sa.ForeignKey("person.id"), primary_key=True),
    )


def downgrade():
    op.drop_table("meeting_participant")
