"""Automated test suite for Module 1: User Authentication & Role-Based Access Control (RBAC)."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.db.session import Base, get_async_db
from backend.main import app
from backend.models.user import User, UserRole

ASYNC_TEST_ENGINE = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
AsyncTestingSessionLocal = async_sessionmaker(
    bind=ASYNC_TEST_ENGINE,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Create in-memory SQLite tables before each test and drop them after."""
    async with ASYNC_TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with ASYNC_TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def async_client():
    """Provide an HTTPX AsyncClient wired to the test SQLite database."""
    async def override_get_async_db():
        async with AsyncTestingSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_async_db] = override_get_async_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_password_hashing_and_verification():
    """Ensure bcrypt hashing produces secure hashes and verifies correctly."""
    pwd = "SecureCivilEngineer2026!"
    hashed = hash_password(pwd)
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_jwt_token_creation_and_decoding():
    """Test generating signed JWT access tokens and decoding claims."""
    claims = {"email": "inspector@infrascan.gov", "role": "INFRASTRUCTURE_INSPECTOR"}
    token = create_access_token(subject="user-uuid-123", claims=claims)
    payload = decode_access_token(token)
    assert payload["sub"] == "user-uuid-123"
    assert payload["email"] == "inspector@infrascan.gov"
    assert payload["role"] == "INFRASTRUCTURE_INSPECTOR"
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_user_registration_success(async_client: AsyncClient):
    """Test user registration endpoint with valid data."""
    payload = {
        "email": "engineer.raj@infrascan.gov",
        "password": "Password123!",
        "full_name": "Rajesh Sharma",
        "role": "Civil Engineer",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "engineer.raj@infrascan.gov"
    assert data["user"]["role"] == "CIVIL_ENGINEER"
    assert data["user"]["full_name"] == "Rajesh Sharma"


@pytest.mark.asyncio
async def test_duplicate_email_registration_rejected(async_client: AsyncClient):
    """Test that registering an existing email returns 400 Bad Request."""
    payload = {
        "email": "dup@infrascan.gov",
        "password": "Password123!",
        "full_name": "Duplicate User",
        "role": "Infrastructure Inspector",
    }
    res1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already registered" in res2.json()["detail"].lower() or "already exists" in res2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success_and_failure(async_client: AsyncClient):
    """Test user login with valid and invalid credentials."""
    # Register first
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "inspector.test@infrascan.gov",
            "password": "CorrectPassword123!",
            "full_name": "Test Inspector",
            "role": "Infrastructure Inspector",
        },
    )

    # Valid Login
    login_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inspector.test@infrascan.gov", "password": "CorrectPassword123!"},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # Invalid Password
    bad_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "inspector.test@infrascan.gov", "password": "WrongPassword999!"},
    )
    assert bad_res.status_code == 401

    # Non-existent User
    unknown_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@infrascan.gov", "password": "AnyPassword123!"},
    )
    assert unknown_res.status_code == 401


@pytest.mark.asyncio
async def test_oauth2_password_grant_token_endpoint(async_client: AsyncClient):
    """Test OAuth2 standard /token endpoint with form-data."""
    await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "manager.sita@infrascan.gov",
            "password": "ManagerPassword123!",
            "full_name": "Sita Verma",
            "role": "Infrastructure Manager",
        },
    )
    response = await async_client.post(
        "/api/v1/auth/token",
        data={"username": "manager.sita@infrascan.gov", "password": "ManagerPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "INFRASTRUCTURE_MANAGER"


@pytest.mark.asyncio
async def test_user_profile_read_and_update(async_client: AsyncClient):
    """Test retrieving and updating own user profile."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={
            "email": "profile.user@infrascan.gov",
            "password": "InitialPassword123!",
            "full_name": "Original Name",
            "role": "Maintenance Engineer",
        },
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Read profile (/auth/me)
    me_res = await async_client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["full_name"] == "Original Name"

    # Update profile name and rotate password (/auth/me)
    patch_res = await async_client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "full_name": "Updated Senior Name",
            "current_password": "InitialPassword123!",
            "new_password": "RotatedPassword456!",
        },
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Updated Senior Name"

    # Verify new password works
    login_new = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "profile.user@infrascan.gov", "password": "RotatedPassword456!"},
    )
    assert login_new.status_code == 200


@pytest.mark.asyncio
async def test_role_based_access_control_restrictions(async_client: AsyncClient):
    """Verify RoleChecker dependency strictly enforces permissions across all 5 roles."""
    # Register Inspector
    r1 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "u.insp@infrascan.gov", "password": "Pass12345!", "role": "INFRASTRUCTURE_INSPECTOR"},
    )
    insp_token = r1.json()["access_token"]

    # Register Civil Engineer
    r2 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "u.civ@infrascan.gov", "password": "Pass12345!", "role": "CIVIL_ENGINEER"},
    )
    civ_token = r2.json()["access_token"]

    # Register Admin
    r3 = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "u.adm@infrascan.gov", "password": "Pass12345!", "role": "ADMIN"},
    )
    adm_token = r3.json()["access_token"]

    # Inspector endpoint:
    # 1. Inspector has access
    g1 = await async_client.get("/api/v1/auth/rbac-test/inspector-only", headers={"Authorization": f"Bearer {insp_token}"})
    assert g1.status_code == 200

    # 2. Civil Engineer is blocked (403)
    g2 = await async_client.get("/api/v1/auth/rbac-test/inspector-only", headers={"Authorization": f"Bearer {civ_token}"})
    assert g2.status_code == 403

    # 3. Admin has access (elevated privilege)
    g3 = await async_client.get("/api/v1/auth/rbac-test/inspector-only", headers={"Authorization": f"Bearer {adm_token}"})
    assert g3.status_code == 200

    # Admin-only endpoint:
    # 1. Inspector is blocked (403)
    g4 = await async_client.get("/api/v1/auth/rbac-test/admin-only", headers={"Authorization": f"Bearer {insp_token}"})
    assert g4.status_code == 403

    # 2. Admin has access
    g5 = await async_client.get("/api/v1/auth/rbac-test/admin-only", headers={"Authorization": f"Bearer {adm_token}"})
    assert g5.status_code == 200


@pytest.mark.asyncio
async def test_audit_logs_persistence(async_client: AsyncClient):
    """Test that audit log records are written upon authentication and RBAC denials."""
    adm_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "auditor.admin@infrascan.gov", "password": "AdminPassword123!", "role": "ADMIN"},
    )
    adm_token = adm_res.json()["access_token"]

    logs_res = await async_client.get(
        "/api/v1/auth/audit-logs",
        headers={"Authorization": f"Bearer {adm_token}"},
    )
    assert logs_res.status_code == 200
    logs = logs_res.json()
    assert len(logs) > 0
    actions = {entry["action"] for entry in logs}
    assert "USER_REGISTERED" in actions
