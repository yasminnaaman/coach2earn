"""Add coach_availability table for structured scheduling.

Revision ID: 20261111_phase6_bookings
Revises: 20261111_order_references
Create Date: 2026-11-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261111_phase6_bookings"
down_revision: Union[str, None] = "20261111_order_references"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "coach_availability",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("coach_profile_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=True),
        sa.Column("specific_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("starts_at_utc", sa.String(5), nullable=False),
        sa.Column("ends_at_utc", sa.String(5), nullable=False),
        sa.Column("slot_duration_minutes", sa.SmallInteger(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "weekday IS NULL OR (weekday >= 1 AND weekday <= 7)",
            name="weekday_range",
        ),
        sa.CheckConstraint(
            "(weekday IS NULL) != (specific_date IS NULL)",
            name="availability_type_exclusive",
        ),
        sa.CheckConstraint("slot_duration_minutes > 0", name="slot_duration_positive"),
        sa.CheckConstraint("starts_at_utc < ends_at_utc", name="availability_window_order"),
        sa.ForeignKeyConstraint(
            ["coach_profile_id"],
            ["coach_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coach_availability_coach_active",
        "coach_availability",
        ["coach_profile_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_coach_availability_coach_active", table_name="coach_availability")
    op.drop_table("coach_availability")
