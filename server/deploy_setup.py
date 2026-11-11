#!/usr/bin/env python3
"""
Render build setup script — idempotent, safe to run on every deploy.

Handles three DB states:
  A. Fresh DB (no alembic_version)           → run all migrations from scratch
  B. Version table exists, schema is intact  → widen version_num column, upgrade to head
  C. Version table exists but schema is broken/partial (tables missing)
                                             → drop and recreate the entire public schema,
                                               then run all migrations from scratch
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SERVER_DIR))

from sqlalchemy import create_engine, inspect, text  # noqa: E402
from app.core.config import get_settings             # noqa: E402


def run(*cmd: str) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    rc = subprocess.run(list(cmd), cwd=str(SERVER_DIR)).returncode
    if rc != 0:
        sys.exit(rc)


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_url)
    insp = inspect(engine)

    has_version_table = insp.has_table("alembic_version")
    # Core tables that must ALL exist for the schema to be considered intact
    EXPECTED = ["users", "player_profiles", "coach_profiles", "coaching_packages"]
    missing = [t for t in EXPECTED if not insp.has_table(t)]

    with engine.begin() as conn:
        if not has_version_table and not missing:
            # Case A-full: no version table, but tables exist from a manual setup
            # Just stamp base and upgrade normally
            print("Tables exist but no alembic_version — will run full upgrade.")

        elif not has_version_table:
            # Case A: completely fresh DB
            print("Fresh database — running full migration.")

        elif missing:
            # Case C: partial schema — drop everything and start clean
            print(f"Broken schema (missing tables: {missing}).")
            print("Dropping and recreating public schema to start clean...")
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
            print("Schema reset complete.")

        else:
            # Case B: schema is intact — widen version column and upgrade
            print("Schema intact. Widening alembic_version.version_num to VARCHAR(64).")
            conn.execute(text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(64)"
            ))

    engine.dispose()

    run("alembic", "upgrade", "head")
    run("python", "-m", "app.seed_specialisations")
    print("Deploy setup complete.")


if __name__ == "__main__":
    main()
