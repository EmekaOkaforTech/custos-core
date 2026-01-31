"""Add NAS backup target configuration table.

Revision ID: 0022_nas_backup_target
Revises: 0021_network_settings
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_nas_backup_target"
down_revision = "0021_network_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nas_backup_target",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("protocol", sa.String(), nullable=False),
        sa.Column("host", sa.String(), nullable=True),
        sa.Column("share", sa.String(), nullable=True),
        sa.Column("mount_path", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("password", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_backup_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("nas_backup_target")
