"""Add oauth_state table for CSRF protection.

Revision ID: 0016_oauth_state_table
Revises: 0015_calendar_oauth_tokens
Create Date: 2026-01-30

Epic 37: Live Calendar Sync - Story 37.1
Adds persistent storage for OAuth state tokens to ensure
production-safe operation across server restarts and multi-process deployments.
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_oauth_state_table"
down_revision = "0015_calendar_oauth_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_state",
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("redirect_uri", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("state"),
    )
    op.create_index("ix_oauth_state_created_at", "oauth_state", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_oauth_state_created_at", table_name="oauth_state")
    op.drop_table("oauth_state")
