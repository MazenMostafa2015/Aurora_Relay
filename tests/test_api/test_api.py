import os
os.environ["DATABASE_URL"] = "sqlite:///./data/test_api.db"
os.environ["JWT_SECRET_KEY"] = "test-secret"

from fastapi.testclient import TestClient

from app.main import app
from app.database.session import engine
from app.database.models import Base

Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)


def test_health_and_openapi():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_register_login_task_crud():
    with TestClient(app) as client:
        registered = client.post("/api/v1/auth/register", json={"username":"alice","email":"alice@example.com","password":"password123"})
        assert registered.status_code == 201
        login = client.post("/api/v1/auth/login", json={"username":"alice","password":"password123"})
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        created = client.post("/api/v1/tasks", json={"order":"write a report", "start_immediately":False}, headers=headers)
        assert created.status_code == 201
        task_id = created.json()["id"]
        assert client.get(f"/api/v1/tasks/{task_id}", headers=headers).status_code == 200
        assert client.get("/api/v1/tasks", headers=headers).json()["total"] == 1
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
        assert client.get("/api/v1/tasks", headers=headers).status_code == 401


def test_duplicate_registration_rejected():
    with TestClient(app) as client:
        client.post("/api/v1/auth/register", json={"username":"bob","email":"bob@example.com","password":"password123"})
        response = client.post("/api/v1/auth/register", json={"username":"bob","email":"bob2@example.com","password":"password123"})
        assert response.status_code == 400
