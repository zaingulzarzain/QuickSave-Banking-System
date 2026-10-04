"""Database engine + session factory."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core.config import settings

# Use normalized URL (handles postgres:// → postgresql+psycopg:// for PaaS)
db_url = settings.database_url_normalized

connect_args = (
    {"check_same_thread": False}
    if db_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    db_url, connect_args=connect_args, pool_pre_ping=True
)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
