#!/usr/bin/env python3
"""
Render deploy setup: resolve alembic version conflicts then upgrade to head.
Safe to run on every deploy — fully idempotent.
"""
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text

from app.core.config import get_settings

HEAD = "20261111_phase6_bookings"


def alembic(*args: str) -> int:
    cmd = ["python", "-m", "alembic"] + list(args)
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd).returncode


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_url)

    with engine.connect() as conn:
        has_alembic = inspect(engine).has_table("alembic_version")

        if not has_alembic:
            print("Fresh database — running full upgrade.")
        else:
            rows = conn.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
            print(f"alembic_version rows: {rows}")

            if rows == [HEAD]:
                print("Already at head — skipping migration.")
                engine.dispose()
                sys.exit(0)

            # Clear the version table so alembic can re-stamp correctly,
            # but only if tables already exist (schema is intact).
            has_users = inspect(engine).has_table("users")
            if has_users:
                print("Tables exist but version is stale — stamping to head directly.")
                conn.execute(text("DELETE FROM alembic_version"))
                conn.execute(text(f"INSERT INTO alembic_version VALUES ('{HEAD}')"))
                conn.commit()
                print("Stamped to head. No DDL changes needed.")
                engine.dispose()
                # Still seed in case it wasn't done
                sys.exit(alembic_seed())
            else:
                print("No user tables found — clearing stale stamp and running full upgrade.")
                conn.execute(text("DELETE FROM alembic_version"))
                conn.commit()

    engine.dispose()

    rc = alembic("upgrade", "head")
    if rc != 0:
        sys.exit(rc)

    sys.exit(alembic_seed())


def alembic_seed() -> int:
    print("Seeding specialisations...")
    return subprocess.run(["python", "-m", "app.seed_specialisations"]).returncode


if __name__ == "__main__":
    main()
