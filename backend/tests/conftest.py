"""Pytest fixtures — isolated in-memory SQLite + TestClient."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

os.environ["QUICKSAVE_TESTING"] = "1"  # disable lifespan seeding

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from backend.app.core.security import create_access_token  # noqa: E402
from backend.app.db.base import Base  # noqa: E402
from backend.app.db.session import get_db  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import User  # noqa: E402
from backend.app.core.security import get_password_hash  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture()
def db(engine):
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False,
                           expire_on_commit=False)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def user_factory(db):
    counter = {"n": 0}

    def make(email_prefix="user", is_admin=False):
        counter["n"] += 1
        user = User(
            email=f"{email_prefix}{counter['n']}@example.com",
            full_name=f"Test {email_prefix.title()}",
            hashed_password=get_password_hash("password123"),
            is_admin=is_admin,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return make


@pytest.fixture()
def auth_headers(user_factory):
    def make(user):
        token = create_access_token(subject=str(user.id))
        return {"Authorization": f"Bearer {token}"}

    return make
