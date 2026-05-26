from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./test_agent_governance_gateway.db"
os.environ["JWT_SECRET"] = "test-secret-key-32-byte-minimum-value"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEMO_SEED_ENABLED"] = "false"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
