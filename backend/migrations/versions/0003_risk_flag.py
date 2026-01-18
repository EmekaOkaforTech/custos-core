"""add risk flag

Revision ID: 0003_risk_flag
Revises: 0002_meeting_participant
Create Date: 2026-01-17
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_risk_flag"
down_revision = "0002_meeting_participant"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "risk_flag",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), sa.ForeignKey("source_record.id"), nullable=False),
        sa.Column("flag_type", sa.String(), nullable=False),
        sa.Column("rule_id", sa.String(), nullable=False),
        sa.Column("excerpt", sa.String(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("risk_flag")
