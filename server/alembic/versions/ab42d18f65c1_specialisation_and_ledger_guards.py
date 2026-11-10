"""Add canonical specialisation checks and SQLite ledger triggers.

Revision ID: ab42d18f65c1
Revises: 6f7ec5e69cea
Create Date: 2026-11-10
"""

from __future__ import annotations

import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ab42d18f65c1"
down_revision: Union[str, None] = "6f7ec5e69cea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Fail without changing catalog data if pre-existing rows do not meet the
    # new canonical format. This is safer than silently rewriting live slugs.
    catalog = sa.table(
        "specialisations",
        sa.column("name", sa.String()),
        sa.column("slug", sa.String()),
    )
    for name, slug in bind.execute(sa.select(catalog.c.name, catalog.c.slug)):
        if not name or not name.strip() or not slug or not _SLUG_PATTERN.fullmatch(slug):
            raise RuntimeError(
                "Existing specialisation data must be normalized before this migration"
            )

    if dialect == "postgresql":
        op.create_check_constraint(
            op.f("ck_specialisations_name_nonempty"),
            "specialisations",
            "length(trim(name)) > 0",
        )
        op.create_check_constraint(
            op.f("ck_specialisations_slug_format_postgresql"),
            "specialisations",
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'",
        )
    elif dialect == "sqlite":
        with op.batch_alter_table("specialisations") as batch_op:
            batch_op.create_check_constraint(
                op.f("ck_specialisations_name_nonempty"), "length(trim(name)) > 0"
            )
            batch_op.create_check_constraint(
                op.f("ck_specialisations_slug_format_sqlite"),
                "slug <> '' AND slug NOT GLOB '*[^a-z0-9-]*' "
                "AND slug NOT GLOB '-*' AND slug NOT GLOB '*-' AND slug NOT GLOB '*--*'",
            )
        op.execute(
            """
            CREATE TRIGGER points_transactions_no_update
            BEFORE UPDATE ON points_transactions
            BEGIN
                SELECT RAISE(ABORT, 'points_transactions is append-only');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER points_transactions_no_delete
            BEFORE DELETE ON points_transactions
            BEGIN
                SELECT RAISE(ABORT, 'points_transactions is append-only');
            END
            """
        )
    else:
        raise RuntimeError(f"Unsupported migration dialect: {dialect}")


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.drop_constraint(
            op.f("ck_specialisations_slug_format_postgresql"),
            "specialisations",
            type_="check",
        )
        op.drop_constraint(
            op.f("ck_specialisations_name_nonempty"),
            "specialisations",
            type_="check",
        )
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER points_transactions_no_update")
        op.execute("DROP TRIGGER points_transactions_no_delete")
        with op.batch_alter_table("specialisations") as batch_op:
            batch_op.drop_constraint(
                op.f("ck_specialisations_slug_format_sqlite"), type_="check"
            )
            batch_op.drop_constraint(
                op.f("ck_specialisations_name_nonempty"), type_="check"
            )
    else:
        raise RuntimeError(f"Unsupported migration dialect: {dialect}")
