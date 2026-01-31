"""Add multi-calendar support fields.

Story 37.5: Multi-Calendar Support
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_multi_calendar_support"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add name field to CalendarConnection for display
    op.add_column("calendar_connection", sa.Column("name", sa.String, nullable=True))

    # Add calendar_source_id to Meeting to track which calendar it came from
    op.add_column("meeting", sa.Column("calendar_source_id", sa.String, nullable=True))
    op.create_index("ix_meeting_calendar_source_id", "meeting", ["calendar_source_id"])


def downgrade() -> None:
    op.drop_index("ix_meeting_calendar_source_id", table_name="meeting")
    op.drop_column("meeting", "calendar_source_id")
    op.drop_column("calendar_connection", "name")
