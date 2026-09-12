"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-03-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_user_email", "user", ["email"])
    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("supplier", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index("ix_product_sku", "product", ["sku"])
    op.create_table(
        "thread",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_thread_owner_user_id", "thread", ["owner_user_id"])
    op.create_table(
        "user_capability",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "capability", name="uq_user_capability"),
    )
    op.create_table(
        "order",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_reference", sa.String(length=64), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("supplier", sa.String(length=255), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["requested_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_order_idempotency_key"),
        sa.UniqueConstraint("order_reference"),
    )
    op.create_index("ix_order_order_reference", "order", ["order_reference"])
    op.create_table(
        "email_message",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=512), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sent_by", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["sent_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_email_idempotency_key"),
    )
    op.create_table(
        "document",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("tool", sa.String(length=128), nullable=False),
        sa.Column("arguments_json", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(length=64), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["thread.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "document_chunk",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_or_section", sa.String(length=128), nullable=False),
        sa.Column("chroma_id", sa.String(length=128), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chroma_id"),
    )


def downgrade() -> None:
    op.drop_table("document_chunk")
    op.drop_table("audit_log")
    op.drop_table("document")
    op.drop_table("email_message")
    op.drop_table("order")
    op.drop_table("user_capability")
    op.drop_table("thread")
    op.drop_table("product")
    op.drop_table("user")
