"""Add email field to Person for calendar attendee matching.

Story 37.3: Attendee Extraction and Person Matching
"""

from alembic import op
import sqlalchemy as sa


revision = "0018"
down_revision = "0017_calendar_sync_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("person", sa.Column("email", sa.String, nullable=True))
    op.create_index("ix_person_email", "person", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_person_email", table_name="person")
    op.drop_column("person", "email")
