"""Isolated test fixtures.

SQLite is the default engine for all tests.  When TEST_DATABASE_URL is set to a
disposable PostgreSQL database the same fixtures connect to PostgreSQL instead,
enabling PostgreSQL-specific tests (locking, expression indexes, triggers).

The PostgreSQL database must already have migrations applied:
    alembic upgrade head
"""

import os

os.environ["JWT_SECRET_KEY"] = "d5b05e90c7b8a2f9a4c4d852f2b51d63c2f6b3e18a8e75d2f9c0b8a1d6e4c731"

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
import app.models  # noqa: F401

_TEST_DATABASE_URL: str | None = os.getenv("TEST_DATABASE_URL")


@pytest.fixture
def db_engine():
    if _TEST_DATABASE_URL:
        # PostgreSQL path — migrations must already be applied.
        engine = create_engine(_TEST_DATABASE_URL, poolclass=NullPool)
        # Truncate all tables in reverse dependency order before each test.
        with engine.begin() as conn:
            conn.execute(text("SET session_replication_role = replica"))
            for tbl in reversed(Base.metadata.sorted_tables):
                conn.execute(tbl.delete())
            conn.execute(text("SET session_replication_role = DEFAULT"))
        try:
            yield engine
        finally:
            engine.dispose()
    else:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record) -> None:
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        Base.metadata.create_all(engine)
        try:
            yield engine
        finally:
            Base.metadata.drop_all(engine)
            engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(db_engine):
    """FastAPI client with request-scoped sessions over an isolated test DB."""
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    session_factory = sessionmaker(bind=db_engine, expire_on_commit=False)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, backend_options={"use_uvloop": True}) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
