"""Add media_path to ingestion_job for audio capture"""

from alembic import op
import sqlalchemy as sa

revision = "0027_audio_capture"
down_revision = "0026_inference_task"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("ingestion_job", sa.Column("media_path", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("ingestion_job", "media_path")
