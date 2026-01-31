"""Add override tracking fields to Meeting for sync conflict resolution.

Story 37.4: Sync Conflict Resolution
"""

from alembic import op
import sqlalchemy as sa


revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("meeting", sa.Column("local_override", sa.Boolean, nullable=False, server_default="0"))
    op.add_column("meeting", sa.Column("calendar_title", sa.String, nullable=True))
    op.add_column("meeting", sa.Column("calendar_starts_at", sa.DateTime, nullable=True))
    op.add_column("meeting", sa.Column("calendar_ends_at", sa.DateTime, nullable=True))


def downgrade() -> None:
    op.drop_column("meeting", "calendar_ends_at")
    op.drop_column("meeting", "calendar_starts_at")
    op.drop_column("meeting", "calendar_title")
    op.drop_column("meeting", "local_override")
