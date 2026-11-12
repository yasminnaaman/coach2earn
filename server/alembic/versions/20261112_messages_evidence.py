"""Add messages and player_evidence tables.

Revision ID: 20261112_messages_evidence
Revises: 20261111_phase6_bookings
Create Date: 2026-11-12
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261112_messages_evidence"
down_revision: Union[str, None] = "20261111_phase6_bookings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sender_user_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_user_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recipient_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_messages_sender_created", "messages", ["sender_user_id", "created_at"])
    op.create_index("ix_messages_recipient_created", "messages", ["recipient_user_id", "created_at"])

    op.create_table(
        "player_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(40), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_player_evidence_user_id", "player_evidence", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_player_evidence_user_id", table_name="player_evidence")
    op.drop_table("player_evidence")
    op.drop_index("ix_messages_recipient_created", table_name="messages")
    op.drop_index("ix_messages_sender_created", table_name="messages")
    op.drop_table("messages")
