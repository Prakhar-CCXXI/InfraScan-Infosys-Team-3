"""Unit and integration tests for user authentication and login endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.session import Base, get_db
from backend.main import app
from backend.models.user import User  # noqa: F401
from backend.services.auth_service import hash_password

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest.fixture()
def client():
    """Setup isolated SQLite in-memory test database and client."""
    Base.metadata.create_all(bind=TEST_ENGINE)

    # Seed test users
    with TestingSessionLocal() as db:
        test_user = User(
            id=10,
            email="testuser@example.com",
            hashed_password=hash_password("Password123"),
            role="Civil Engineer",
        )
        db.add(test_user)
        db.commit()

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


def test_login_successful_with_id_password_email_role(client):
    """Test user login endpoint with valid ID, password, email, and role."""
    payload = {
        "id": 10,
        "password": "Password123",
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["id"] == 10
    assert data["user"]["email"] == "testuser@example.com"
    assert data["user"]["role"] == "Civil Engineer"
    assert data["message"] == "Login successful"


def test_login_with_string_id(client):
    """Test login when ID is supplied as a string or formatted identifier."""
    payload = {
        "id": "10",
        "password": "Password123",
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 200
    assert response.json()["user"]["id"] == 10


def test_login_via_users_login_route(client):
    """Test that login is also accessible at /users/login and /api/v1/auth/login."""
    payload = {
        "id": 10,
        "password": "Password123",
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    }
    res_users = client.post("/users/login", json=payload)
    assert res_users.status_code == 200
    assert res_users.json()["user"]["id"] == 10

    res_api = client.post("/api/v1/auth/login", json=payload)
    assert res_api.status_code == 200
    assert res_api.json()["user"]["id"] == 10


def test_login_missing_fields_validation_error(client):
    """Test that omitting ID, password, email, or role produces validation error."""
    # Missing ID
    res1 = client.post("/auth/login", json={
        "password": "Password123",
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    })
    assert res1.status_code == 422

    # Missing Password
    res2 = client.post("/auth/login", json={
        "id": 10,
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    })
    assert res2.status_code == 422

    # Missing Email
    res3 = client.post("/auth/login", json={
        "id": 10,
        "password": "Password123",
        "role": "Civil Engineer",
    })
    assert res3.status_code == 422

    # Missing Role
    res4 = client.post("/auth/login", json={
        "id": 10,
        "password": "Password123",
        "email": "testuser@example.com",
    })
    assert res4.status_code == 422


def test_login_invalid_password(client):
    """Test rejection when incorrect password is provided."""
    payload = {
        "id": 10,
        "password": "IncorrectPassword",
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert "Invalid password" in response.json()["detail"]


def test_login_invalid_role(client):
    """Test rejection when non-matching role is provided."""
    payload = {
        "id": 10,
        "password": "Password123",
        "email": "testuser@example.com",
        "role": "Accountant",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert "Role mismatch" in response.json()["detail"]


def test_login_id_mismatch(client):
    """Test rejection when ID does not match email account."""
    payload = {
        "id": 999,
        "password": "Password123",
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert "mismatch" in response.json()["detail"].lower()


def test_login_user_not_found(client):
    """Test rejection when user does not exist."""
    payload = {
        "id": 888,
        "password": "Password123",
        "email": "nonexistent@example.com",
        "role": "Civil Engineer",
    }
    response = client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert "not found" in response.json()["detail"].lower()


def test_register_and_login_new_user(client):
    """Test registering a new user and logging in with their credentials."""
    reg_payload = {
        "id": 50,
        "email": "newengineer@example.com",
        "password": "SecurePassword99",
        "role": "Maintenance Engineer",
        "name": "Jane Engineer",
    }
    reg_response = client.post("/auth/register", json=reg_payload)
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert reg_data["user"]["id"] == 50
    assert reg_data["user"]["email"] == "newengineer@example.com"

    # Now login with the newly created account
    login_payload = {
        "id": 50,
        "password": "SecurePassword99",
        "email": "newengineer@example.com",
        "role": "Maintenance Engineer",
    }
    login_response = client.post("/auth/login", json=login_payload)
    assert login_response.status_code == 200
    assert login_response.json()["user"]["id"] == 50


def test_list_users_and_get_user_by_id(client):
    """Test listing all users and retrieving user by ID."""
    res_list = client.get("/users")
    assert res_list.status_code == 200
    users = res_list.json()
    assert len(users) >= 1
    assert any(u["email"] == "testuser@example.com" for u in users)

    res_user = client.get("/users/10")
    assert res_user.status_code == 200
    assert res_user.json()["email"] == "testuser@example.com"


def test_get_current_user_me(client):
    """Test getting current user with bearer token."""
    login_payload = {
        "id": 10,
        "password": "Password123",
        "email": "testuser@example.com",
        "role": "Civil Engineer",
    }
    login_res = client.post("/auth/login", json=login_payload)
    token = login_res.json()["token"]

    me_res = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["id"] == 10
    assert me_res.json()["email"] == "testuser@example.com"
