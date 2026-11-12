"""Add profile preferences and auditable qualification review records.

Revision ID: 20261111_phase4_profiles
Revises: 20261111_merge_heads
Create Date: 2026-11-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261111_phase4_profiles"
down_revision: Union[str, None] = "20261111_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("player_profiles") as batch_op:
        batch_op.add_column(sa.Column("gaming_experience_years", sa.SmallInteger(), nullable=True))
        batch_op.add_column(sa.Column("budget_amount", sa.Numeric(12, 2), nullable=True))
        batch_op.add_column(sa.Column("budget_currency", sa.String(3), nullable=True))
        batch_op.create_check_constraint(
            op.f("ck_player_profiles_gaming_experience_nonnegative"),
            "gaming_experience_years IS NULL OR gaming_experience_years >= 0",
        )
        batch_op.create_check_constraint(
            op.f("ck_player_profiles_budget_nonnegative"),
            "budget_amount IS NULL OR budget_amount >= 0",
        )
        batch_op.create_check_constraint(
            op.f("ck_player_profiles_budget_currency_pair"),
            "(budget_amount IS NULL) = (budget_currency IS NULL)",
        )
        batch_op.create_check_constraint(
            op.f("ck_player_profiles_budget_currency_iso_length"),
            "budget_currency IS NULL OR length(budget_currency) = 3",
        )
    op.create_table(
        "player_games",
        sa.Column("player_profile_id", sa.Uuid(), nullable=False),
        sa.Column("specialisation_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["player_profile_id"], ["player_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["specialisation_id"], ["specialisations.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("player_profile_id", "specialisation_id"),
    )
    op.add_column("coach_profiles", sa.Column("coaching_goals", sa.Text(), nullable=True))
    qualification_status_type = sa.Enum(
        "pending",
        "approved",
        "rejected",
        "needs_more_evidence",
        name="qualification_verification_status",
        native_enum=False,
        create_constraint=True,
    )
    with op.batch_alter_table("coach_qualifications") as batch_op:
        batch_op.add_column(
            sa.Column(
                "verification_status",
                qualification_status_type,
                nullable=True,
            )
        )
    op.execute(
        "UPDATE coach_qualifications SET verification_status = 'pending' "
        "WHERE verification_status IS NULL"
    )
    with op.batch_alter_table("coach_qualifications") as batch_op:
        batch_op.alter_column(
            "verification_status",
            existing_type=qualification_status_type,
            nullable=False,
        )
    op.create_table(
        "coach_qualification_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("qualification_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "needs_more_evidence",
                name="qualification_review_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["qualification_id"], ["coach_qualifications.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_coach_qualification_reviews_qualification",
        "coach_qualification_reviews",
        ["qualification_id", "reviewed_at"],
    )
    op.create_index(
        "ix_coach_qualification_reviews_reviewer",
        "coach_qualification_reviews",
        ["reviewer_user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_coach_qualification_reviews_reviewer", table_name="coach_qualification_reviews"
    )
    op.drop_index(
        "ix_coach_qualification_reviews_qualification",
        table_name="coach_qualification_reviews",
    )
    op.drop_table("coach_qualification_reviews")
    with op.batch_alter_table("coach_qualifications") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_coach_qualifications_qualification_verification_status"),
            type_="check",
        )
        batch_op.drop_column("verification_status")
    op.drop_column("coach_profiles", "coaching_goals")
    op.drop_table("player_games")
    with op.batch_alter_table("player_profiles") as batch_op:
        batch_op.drop_constraint(
            op.f("ck_player_profiles_budget_currency_iso_length"), type_="check"
        )
        batch_op.drop_constraint(
            op.f("ck_player_profiles_budget_currency_pair"), type_="check"
        )
        batch_op.drop_constraint(op.f("ck_player_profiles_budget_nonnegative"), type_="check")
        batch_op.drop_constraint(
            op.f("ck_player_profiles_gaming_experience_nonnegative"), type_="check"
        )
        batch_op.drop_column("budget_currency")
        batch_op.drop_column("budget_amount")
        batch_op.drop_column("gaming_experience_years")
