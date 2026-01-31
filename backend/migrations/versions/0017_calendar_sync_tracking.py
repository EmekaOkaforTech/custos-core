"""Add calendar sync tracking fields.

Revision ID: 0017_calendar_sync_tracking
Revises: 0016_oauth_state_table
Create Date: 2026-01-30

Epic 37: Live Calendar Sync - Story 37.2
Adds fields to track sync status and handle meeting deletions.
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_calendar_sync_tracking"
down_revision = "0016_oauth_state_table"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add sync tracking to calendar_connection
    op.add_column(
        "calendar_connection",
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "calendar_connection",
        sa.Column("sync_error", sa.String(), nullable=True),
    )

    # Add cancelled_at to meeting for soft deletion
    op.add_column(
        "meeting",
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_meeting_cancelled_at", "meeting", ["cancelled_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_meeting_cancelled_at", table_name="meeting")
    op.drop_column("meeting", "cancelled_at")
    op.drop_column("calendar_connection", "sync_error")
    op.drop_column("calendar_connection", "last_sync_at")
