"""Add OAuth token fields to calendar_connection.

Revision ID: 0015_calendar_oauth_tokens
Revises: 0014_person_tag
Create Date: 2026-01-30

Epic 37: Live Calendar Sync - Story 37.1
Adds refresh_token, token_expires_at, last_refresh_at, and provider_user_id
to support OAuth2 authentication with Google Calendar and Microsoft Outlook.
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_calendar_oauth_tokens"
down_revision = "0014_person_tag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if calendar_connection table exists, create if not
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "calendar_connection" not in tables:
        # Create the full table
        op.create_table(
            "calendar_connection",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("provider", sa.String(), nullable=False),
            sa.Column("scopes", sa.Text(), nullable=False),
            sa.Column("token", sa.Text(), nullable=False),
            sa.Column("refresh_token", sa.Text(), nullable=True),
            sa.Column("token_expires_at", sa.DateTime(), nullable=True),
            sa.Column("last_refresh_at", sa.DateTime(), nullable=True),
            sa.Column("provider_user_id", sa.String(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_calendar_connection_provider", "calendar_connection", ["provider"], unique=False)
    else:
        # Add new columns to existing table
        with op.batch_alter_table("calendar_connection") as batch_op:
            batch_op.add_column(sa.Column("refresh_token", sa.Text(), nullable=True))
            batch_op.add_column(sa.Column("token_expires_at", sa.DateTime(), nullable=True))
            batch_op.add_column(sa.Column("last_refresh_at", sa.DateTime(), nullable=True))
            batch_op.add_column(sa.Column("provider_user_id", sa.String(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "calendar_connection" in tables:
        columns = [col["name"] for col in inspector.get_columns("calendar_connection")]
        with op.batch_alter_table("calendar_connection") as batch_op:
            if "refresh_token" in columns:
                batch_op.drop_column("refresh_token")
            if "token_expires_at" in columns:
                batch_op.drop_column("token_expires_at")
            if "last_refresh_at" in columns:
                batch_op.drop_column("last_refresh_at")
            if "provider_user_id" in columns:
                batch_op.drop_column("provider_user_id")
