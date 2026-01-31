from alembic import op
import sqlalchemy as sa

revision = '0027_summarization_settings'
down_revision = '0026_inference_task'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'summarization_settings',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('max_input_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table('summarization_settings')
