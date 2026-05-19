"""initial schema

Revision ID: 2db2b4ec468c
Revises: 
Create Date: 2026-05-18 17:17:19.028477

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2db2b4ec468c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("file_size", sa.BigInteger, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("uploaded_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("status IN ('PROCESSING','READY','FAILED')", name="documents_status_check"),
    )
    op.create_index("ix_documents_user_id", "documents", ["user_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("document_ids", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("sources", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("role IN ('USER','ASSISTANT')", name="messages_role_check"),
    )
    op.create_index("idx_messages_conv_created", "messages", ["conversation_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_messages_conv_created", "messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_user_id", "conversations")
    op.drop_table("conversations")
    op.drop_index("ix_documents_user_id", "documents")
    op.drop_table("documents")
    op.drop_index("ix_users_email", "users")
    op.drop_table("users")
