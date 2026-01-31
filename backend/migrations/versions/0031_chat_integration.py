"""Add chat integration tables"""

from alembic import op
import sqlalchemy as sa

revision = "0031_chat_integration"
down_revision = "0030_email_integration"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chat_integration",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("secret", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "chat_message",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("channel_id", sa.String(), nullable=True),
        sa.Column("channel_name", sa.String(), nullable=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("user_name", sa.String(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("meeting_id", sa.String(), nullable=True),
        sa.Column("person_id", sa.String(), nullable=True),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("payload_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_chat_message_provider", "chat_message", ["provider"], unique=False)
    op.create_index("ix_chat_message_meeting", "chat_message", ["meeting_id"], unique=False)


def downgrade():
    op.drop_index("ix_chat_message_meeting", table_name="chat_message")
    op.drop_index("ix_chat_message_provider", table_name="chat_message")
    op.drop_table("chat_message")
    op.drop_table("chat_integration")
