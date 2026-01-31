"""Add inference task queue"""

from alembic import op
import sqlalchemy as sa

revision = 0026_inference_task
down_revision = 0025_model_artifact
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        inference_task,
        sa.Column(id, sa.String(), primary_key=True),
        sa.Column(task_type, sa.String(), nullable=False),
        sa.Column(payload, sa.Text(), nullable=True),
        sa.Column(priority, sa.Integer(), nullable=False, server_default=0),
        sa.Column(status, sa.String(), nullable=False),
        sa.Column(error, sa.Text(), nullable=True),
        sa.Column(created_at, sa.DateTime(), nullable=False),
        sa.Column(started_at, sa.DateTime(), nullable=True),
        sa.Column(completed_at, sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_table(inference_task)
