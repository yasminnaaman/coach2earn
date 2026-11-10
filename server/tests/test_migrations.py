"""Alembic upgrade and rollback checks against a disposable SQLite database."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_initial_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    server_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration-test.sqlite"
    config = Config(str(server_dir / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        existing_tables = set(inspect(engine).get_table_names())
        expected_tables = {
            "users",
            "player_profiles",
            "coach_profiles",
            "coach_qualifications",
            "coach_specialisations",
            "specialisations",
            "coach_verifications",
            "teams",
            "team_memberships",
            "coaching_packages",
            "quotations",
            "orders",
            "bookings",
            "coaching_sessions",
            "points_transactions",
            "bonuses",
            "rewards",
            "reward_redemptions",
            "prizes",
            "coach_earnings",
            "payout_records",
            "payout_allocations",
            "alembic_version",
        }
        assert expected_tables <= existing_tables
        with engine.connect() as connection:
            index_sql = connection.execute(
                text("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_users_email_lower'")
            ).scalar_one()
        assert "lower(email)" in index_sql
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        assert "users" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
