"""Add model artifact registry"""

from alembic import op
import sqlalchemy as sa

revision = "0025_model_artifact"
down_revision = "0024_nas_sync_settings"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "model_artifact",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("format", sa.String(), nullable=True),
        sa.Column("accelerator", sa.String(), nullable=True),
        sa.Column("checksum", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade():
    op.drop_table("model_artifact")
