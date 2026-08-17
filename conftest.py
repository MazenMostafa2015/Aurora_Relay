from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


_default_test_db = Path(__file__).resolve().parent / "data" / "phase8_test.db"
TEST_DB = Path(os.environ.get("AURORA_TEST_DB", _default_test_db)).expanduser().resolve()
TEST_DB.parent.mkdir(parents=True, exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["JWT_SECRET_KEY"] = "test-only-jwt-secret-not-for-production-0123456789-abcdef-0123456789"
os.environ["ALLOWED_HOSTS"] = '["localhost", "127.0.0.1", "testserver"]'
os.environ.setdefault("DEBUG", "false")

from app.database.models import Base  # noqa: E402
from app.database.session import engine  # noqa: E402
from app.main import app  # noqa: E402
from tests.fixtures.test_data import unique_user  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def isolated_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def authenticated_client(client):
    user = unique_user()
    registered = client.post("/api/v1/auth/register", json={"username": user.username, "email": user.email, "password": user.password})
    assert registered.status_code in {200, 201}, registered.text
    login = client.post("/api/v1/auth/login", json={"username": user.username, "password": user.password})
    assert login.status_code == 200, login.text
    client.headers.update({"Authorization": f"Bearer {login.json()['access_token']}"})
    return client
