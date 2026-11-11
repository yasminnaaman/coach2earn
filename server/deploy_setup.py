#!/usr/bin/env python3
"""
Render build setup script.

1. Widens alembic_version.version_num to VARCHAR(64) if it exists and is too
   narrow — our revision IDs are up to 34 characters but Alembic defaults to 32.
2. Runs alembic upgrade head.
3. Seeds specialisations (idempotent).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Ensure server/ is on the path regardless of where this script is invoked from.
SERVER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SERVER_DIR))

from sqlalchemy import create_engine, inspect, text  # noqa: E402

from app.core.config import get_settings  # noqa: E402


def run(*cmd: str) -> None:
    print(f"$ {' '.join(cmd)}", flush=True)
    rc = subprocess.run(list(cmd), cwd=str(SERVER_DIR)).returncode
    if rc != 0:
        sys.exit(rc)


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.sqlalchemy_database_url)

    with engine.begin() as conn:
        if inspect(engine).has_table("alembic_version"):
            # Widen the column so long revision IDs (> 32 chars) fit.
            conn.execute(text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(64)"
            ))
            print("alembic_version.version_num widened to VARCHAR(64).")
        else:
            print("No alembic_version table yet — fresh database.")

    engine.dispose()

    run("alembic", "upgrade", "head")
    run("python", "-m", "app.seed_specialisations")
    print("Deploy setup complete.")


if __name__ == "__main__":
    main()
