from alembic import op
import sqlalchemy as sa

revision = '0030_email_integration'
down_revision = '0029_merge_audio_summarization'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'email_connection',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('host', sa.String(), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False, server_default='993'),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password', sa.String(), nullable=True),
        sa.Column('use_tls', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('poll_interval_minutes', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('last_uid', sa.Integer(), nullable=True),
        sa.Column('last_success', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('last_attempt', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        'email_message',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('message_id', sa.String(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=True),
        sa.Column('from_email', sa.String(), nullable=True),
        sa.Column('to_emails', sa.Text(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('meeting_id', sa.String(), sa.ForeignKey('meeting.id'), nullable=True),
        sa.Column('source_id', sa.String(), sa.ForeignKey('source_record.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_email_message_message_id', 'email_message', ['message_id'], unique=True)
    op.create_index('ix_email_message_thread_id', 'email_message', ['thread_id'])
    op.create_index('ix_email_message_meeting_id', 'email_message', ['meeting_id'])


def downgrade():
    op.drop_index('ix_email_message_meeting_id', table_name='email_message')
    op.drop_index('ix_email_message_thread_id', table_name='email_message')
    op.drop_index('ix_email_message_message_id', table_name='email_message')
    op.drop_table('email_message')
    op.drop_table('email_connection')
