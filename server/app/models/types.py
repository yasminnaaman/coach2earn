"""Shared SQLAlchemy column type helpers."""

from enum import StrEnum

from sqlalchemy import Enum


def enum_column(enum_cls: type[StrEnum], name: str) -> Enum:
    """Store enum values as strings with database-side value constraints."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda values: [item.value for item in values],
    )
