"""Add user accounts table

Revision ID: 0034_user_accounts
Revises: 0033_analytics_daily
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0034_user_accounts"
down_revision = "0033_analytics_daily"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user")
