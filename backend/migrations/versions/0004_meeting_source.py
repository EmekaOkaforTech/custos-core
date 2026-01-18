"""add meeting source

Revision ID: 0004_meeting_source
Revises: 0003_risk_flag
Create Date: 2026-01-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_meeting_source"
down_revision = "0003_risk_flag"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("meeting", sa.Column("source", sa.String(), nullable=True))


def downgrade():
    op.drop_column("meeting", "source")
