"""Add analytics_daily table

Revision ID: 0033_analytics_daily
Revises: 0032_query_history
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0033_analytics_daily"
down_revision = "0032_query_history"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_daily",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("day", sa.Date(), nullable=False, index=True),
        sa.Column("metrics", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("analytics_daily")
