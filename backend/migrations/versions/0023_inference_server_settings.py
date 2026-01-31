"""Add inference server settings to network settings.

Revision ID: 0023_inference_server_settings
Revises: 0022_nas_backup_target
"""

from alembic import op
import sqlalchemy as sa

revision = "0023_inference_server_settings"
down_revision = "0022_nas_backup_target"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("network_settings", sa.Column("inference_url", sa.String(), nullable=True))
    op.add_column("network_settings", sa.Column("inference_enabled", sa.Boolean(), nullable=False, server_default=sa.text("0")))
    op.add_column("network_settings", sa.Column("inference_last_checked", sa.DateTime(), nullable=True))
    op.add_column("network_settings", sa.Column("inference_status", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("network_settings", "inference_status")
    op.drop_column("network_settings", "inference_last_checked")
    op.drop_column("network_settings", "inference_enabled")
    op.drop_column("network_settings", "inference_url")
