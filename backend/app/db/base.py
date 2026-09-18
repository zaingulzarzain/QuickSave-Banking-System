"""SQLAlchemy declarative base + shared helpers."""

import datetime as dt

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def utcnow() -> dt.datetime:
    """Naive UTC timestamp (portable across SQLite/Postgres)."""
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
