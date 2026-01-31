"""Add network_settings table"""

from alembic import op
import sqlalchemy as sa

revision = '0021_network_settings'
down_revision = '0020_multi_calendar_support'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'network_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('discovery_enabled', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('scan_interval_minutes', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('manual_services', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('last_scan_at', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('network_settings')
