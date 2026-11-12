"""Merge authentication and profile database migration heads.

Revision ID: 20261111_merge_heads
Revises: 8a2cd8f11b42, ab42d18f65c1
Create Date: 2026-11-11
"""

from __future__ import annotations

from typing import Sequence, Union


revision: str = "20261111_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "8a2cd8f11b42",
    "ab42d18f65c1",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
