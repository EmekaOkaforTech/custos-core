from alembic import op
import sqlalchemy as sa

revision = '0028_source_record_summaries'
down_revision = '0027_summarization_settings'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('source_record', sa.Column('summary_text', sa.Text(), nullable=True))
    op.add_column('source_record', sa.Column('summary_provider', sa.String(), nullable=True))
    op.add_column('source_record', sa.Column('summary_model', sa.String(), nullable=True))
    op.add_column('source_record', sa.Column('summary_created_at', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('source_record', 'summary_created_at')
    op.drop_column('source_record', 'summary_model')
    op.drop_column('source_record', 'summary_provider')
    op.drop_column('source_record', 'summary_text')
