"""Add NAS sync settings table.

Revision ID: 0024_nas_sync_settings
Revises: 0023_inference_server_settings
"""

from alembic import op
import sqlalchemy as sa

revision = "0024_nas_sync_settings"
down_revision = "0023_inference_server_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nas_sync_settings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("mount_path", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("nas_sync_settings")
