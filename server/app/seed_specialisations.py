"""Idempotently seed the approved game-specialisation catalog entries."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import SpecialisationCategory
from app.models.identity import Specialisation


@dataclass(frozen=True)
class SpecialisationSeed:
    category: SpecialisationCategory
    name: str
    slug: str


# Product documentation names Rocket League as the initial game. Other games
# mentioned in docs are examples only and are intentionally not seeded here.
INITIAL_SPECIALISATIONS = (
    SpecialisationSeed(
        category=SpecialisationCategory.GAME,
        name="Rocket League",
        slug="rocket-league",
    ),
)


class SpecialisationSeedConflict(ValueError):
    """Raised when a seeded slug already identifies different catalog data."""


def seed_specialisations(
    db: Session,
    entries: tuple[SpecialisationSeed, ...] = INITIAL_SPECIALISATIONS,
) -> int:
    """Insert known catalog rows without overwriting existing or conflicting data.

    The operation is atomic and safe to rerun. Returns the number of entries
    verified in the catalog after the operation.
    """
    dialect = db.get_bind().dialect.name
    if dialect not in {"postgresql", "sqlite"}:
        raise RuntimeError(f"Specialisation seeding is unsupported for {dialect}")

    with db.begin():
        for entry in entries:
            insert_statement = (
                pg_insert(Specialisation)
                if dialect == "postgresql"
                else sqlite_insert(Specialisation)
            )
            db.execute(
                insert_statement.values(
                    id=uuid4(),
                    category=entry.category,
                    name=entry.name,
                    slug=entry.slug,
                ).on_conflict_do_nothing(index_elements=[Specialisation.slug])
            )

        existing = {
            row.slug: row
            for row in db.scalars(
                select(Specialisation).where(
                    Specialisation.slug.in_([entry.slug for entry in entries])
                )
            )
        }
        for entry in entries:
            row = existing.get(entry.slug)
            if row is None or row.category != entry.category or row.name != entry.name:
                raise SpecialisationSeedConflict(
                    f"Catalog slug {entry.slug!r} already has different data; no rows were changed"
                )
    return len(entries)


def main() -> int:
    try:
        with SessionLocal() as db:
            count = seed_specialisations(db)
    except SpecialisationSeedConflict as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        # Do not print connection exception text because it may contain a DSN.
        print("Specialisation seeding failed; check database configuration and migration status.", file=sys.stderr)
        return 1

    print(f"Verified {count} initial game specialisation(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
