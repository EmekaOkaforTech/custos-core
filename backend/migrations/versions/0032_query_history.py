"""Add query history table

Revision ID: 0032_query_history
Revises: 0031_chat_integration
Create Date: 2026-01-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0032_query_history"
down_revision = "0031_chat_integration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "query_history",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("intent", sa.String(), nullable=True),
        sa.Column("filters", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("query_history")
