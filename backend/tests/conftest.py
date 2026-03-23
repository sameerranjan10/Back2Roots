"""
conftest.py — Shared pytest fixtures for Alumni Nexus tests.

Uses an in-memory SQLite database so tests run without MySQL and
leave no side effects.  Each test gets a fresh database via the
`db` fixture.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.auth import get_password_hash
from app import models

# ── In-memory SQLite engine for tests ─────────────────────────────────────────
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def db():
    """
    Provide a fresh database session for each test.
    Tables are created before each test and dropped after.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db):
    """
    Provide a FastAPI TestClient with the database dependency overridden
    to use the in-memory test session.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass  # session managed by `db` fixture

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helper factories ───────────────────────────────────────────────────────────

def make_user(
    db,
    name: str       = "Test User",
    email: str      = "test@college.edu",
    password: str   = "password123",
    role: str       = "student",
    college: str    = "Test College",
    skills: str     = "Python, Testing",
    bio: str        = "A test user.",
) -> models.User:
    """Create and persist a User; return the ORM object."""
    user = models.User(
        name=name,
        email=email,
        password=get_password_hash(password),
        role=role,
        college=college,
        skills=skills,
        bio=bio,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_token(client: TestClient, email: str, password: str) -> str:
    """Login and return the JWT access token string."""
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Return Authorization header dict for a given JWT token."""
    return {"Authorization": f"Bearer {token}"}
