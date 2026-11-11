"""Alembic upgrade and rollback checks against a disposable SQLite database."""

from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
import pytest


def test_initial_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    server_dir = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "migration-test.sqlite"
    config = Config(str(server_dir / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(config, "6f7ec5e69cea")
    engine = create_engine(f"sqlite:///{database_path}")
    seeded_id = str(uuid4())
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO specialisations (id, category, name, slug) "
                    "VALUES (:id, 'game', 'Rocket League', 'rocket-league')"
                ),
                {"id": seeded_id},
            )
    finally:
        engine.dispose()

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
            assert connection.execute(
                text("SELECT id FROM specialisations WHERE slug = 'rocket-league'")
            ).scalar_one() == seeded_id
        with engine.connect() as connection:
            index_sql = connection.execute(
                text("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_users_email_lower'")
            ).scalar_one()
        assert "lower(email)" in index_sql

        with engine.begin() as connection:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO specialisations (id, category, name, slug) "
                        "VALUES (:id, 'game', 'Invalid game', 'invalid_slug')"
                    ),
                    {"id": str(uuid4())},
                )

        user_id = str(uuid4())
        transaction_id = str(uuid4())
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users (id, email, password_hash, role, account_status) "
                    "VALUES (:id, 'ledger@example.test', 'hash', 'player', 'active')"
                ),
                {"id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO points_transactions "
                    "(id, user_id, transaction_type, source_type, source_reference, points_delta) "
                    "VALUES (:id, :user_id, 'earned', 'admin_action', 'migration-test', 10)"
                ),
                {"id": transaction_id, "user_id": user_id},
            )
        with engine.begin() as connection:
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(
                    text("UPDATE points_transactions SET points_delta = 20 WHERE id = :id"),
                    {"id": transaction_id},
                )
        with engine.begin() as connection:
            with pytest.raises(IntegrityError, match="append-only"):
                connection.execute(
                    text("DELETE FROM points_transactions WHERE id = :id"),
                    {"id": transaction_id},
                )
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        assert "users" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()
