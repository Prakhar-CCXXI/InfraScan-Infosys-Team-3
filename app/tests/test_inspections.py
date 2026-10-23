import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models.inspection import Inspection  # noqa: F401

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=TEST_ENGINE)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)


def test_create_and_retrieve_inspection(client):
    payload = {
        "infrastructure_name": "City Bridge A",
        "infrastructure_type": "bridge",
        "location": "Jamshedpur, Jharkhand",
        "description": "Visible cracks near the support pillar",
    }
    created = client.post("/inspections/", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["id"] == 1
    assert body["status"] == "pending"
    assert body["infrastructure_name"] == payload["infrastructure_name"]

    fetched = client.get(f"/inspections/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["location"] == payload["location"]


def test_list_inspections(client):
    payload = {
        "infrastructure_name": "Road Section 12",
        "infrastructure_type": "road",
        "location": "Bhopal, Madhya Pradesh",
    }
    assert client.post("/inspections/", json=payload).status_code == 201
    response = client.get("/inspections/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_invalid_payload_returns_422(client):
    response = client.post("/inspections/", json={
        "infrastructure_name": " ",
        "infrastructure_type": "spaceship",
        "location": "X",
        "unexpected": True,
    })
    assert response.status_code == 422


def test_missing_inspection_returns_404(client):
    response = client.get("/inspections/999")
    assert response.status_code == 404
