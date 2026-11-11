"""Add age and auditable guardian-consent records.

Revision ID: 8a2cd8f11b42
Revises: 6f7ec5e69cea
Create Date: 2026-11-11
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a2cd8f11b42"
down_revision: Union[str, None] = "6f7ec5e69cea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("date_of_birth", sa.Date(), nullable=True))
    op.create_table(
        "guardian_consents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("guardian_name", sa.String(length=200), nullable=False),
        sa.Column("guardian_email", sa.String(length=320), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "verified", "rejected", name="guardian_consent_status",
                native_enum=False, create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("consent_version", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_guardian_consents_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guardian_consents")),
        sa.UniqueConstraint("user_id", name=op.f("uq_guardian_consents_user_id")),
    )
    op.create_table(
        "guardian_consent_decisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("consent_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "verified", "rejected", name="guardian_consent_decision_status",
                native_enum=False, create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("evidence_reference", sa.String(length=2048), nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["consent_id"], ["guardian_consents.id"],
            name=op.f("fk_guardian_consent_decisions_consent_id_guardian_consents"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_user_id"], ["users.id"],
            name=op.f("fk_guardian_consent_decisions_reviewer_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_guardian_consent_decisions")),
    )
    op.create_index(
        "ix_guardian_consent_decisions_consent_id",
        "guardian_consent_decisions",
        ["consent_id"],
    )
    op.create_index(
        "ix_guardian_consent_decisions_reviewer_user_id",
        "guardian_consent_decisions",
        ["reviewer_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_guardian_consent_decisions_reviewer_user_id", table_name="guardian_consent_decisions")
    op.drop_index("ix_guardian_consent_decisions_consent_id", table_name="guardian_consent_decisions")
    op.drop_table("guardian_consent_decisions")
    op.drop_table("guardian_consents")
    op.drop_column("users", "date_of_birth")
