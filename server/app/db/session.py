"""Synchronous SQLAlchemy database connection setup."""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def build_engine(database_url: str) -> Engine:
    """Create an engine without opening a connection during app import."""
    return create_engine(database_url, pool_pre_ping=True)


engine = build_engine(get_settings().sqlalchemy_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> None:
    """Raise a SQLAlchemy error if PostgreSQL cannot execute a basic query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
