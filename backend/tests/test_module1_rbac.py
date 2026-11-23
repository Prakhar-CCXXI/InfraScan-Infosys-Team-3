"""Comprehensive test suite for Module 1: User Authentication & Role-Based Access Control (RBAC).

Covers all functional requirements:
1. Registration (201 Created), Argon2 hashing, Duplicate check (409 Conflict)
2. Login (200 OK), Access Token (15-min) & Refresh Token (7-day), 401 on bad credentials / inactive user
3. Refresh Token rotation and revocation (401 on reuse)
4. Logout and token revocation
5. Secure Password Change with Argon2
6. Google OAuth2 flow & safe default role enforcement (never trusting external role)
7. User Profile endpoints: GET/PUT /api/v1/users/me
8. Admin Management: GET /api/v1/admin/users, PATCH /api/v1/admin/users/{id}/role, GET /api/v1/admin/audit-logs (403 for non-admin, 200 for admin)
9. Reusable RBAC dependencies require_role([...])
"""

import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.core.security import decode_access_token, decode_refresh_token, verify_password
from backend.app.db.session import Base, get_async_db
from backend.app.main import app
from backend.app.models.user import User, UserRole
from backend.app.models.audit_log import AuditLog
from backend.scripts.seed_admin import seed_admin

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


# ============================================================================
# 1. Registration & Argon2 Hashing
# ============================================================================

@pytest.mark.asyncio
async def test_register_creates_user_with_argon2_hash(async_client: AsyncClient):
    """Test user registration hashes password with Argon2 and returns 201."""
    payload = {
        "email": "engineer.alice@infrascan.gov",
        "password": "SuperSecretPassword123!",
        "full_name": "Alice Morgan",
        "role": "CIVIL_ENGINEER",
    }
    response = await async_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "engineer.alice@infrascan.gov"
    assert data["user"]["role"] == "CIVIL_ENGINEER"

    # Verify directly in DB that password_hash starts with $argon2id$ (never plain-text)
    async with AsyncTestingSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == "engineer.alice@infrascan.gov"))
        assert user is not None
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password("SuperSecretPassword123!", user.password_hash) is True


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409_conflict(async_client: AsyncClient):
    """Test duplicate registration returns 409 Conflict."""
    payload = {
        "email": "duplicate.user@infrascan.gov",
        "password": "Password123!",
        "full_name": "Duplicate Test",
    }
    r1 = await async_client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = await async_client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already registered" in r2.json()["detail"].lower() or "already exists" in r2.json()["detail"].lower()


# ============================================================================
# 2. Login, Token Lifecycles & 401 Validations
# ============================================================================

@pytest.mark.asyncio
async def test_login_returns_tokens_and_user_details(async_client: AsyncClient):
    """Test login returns 15-min Access Token, 7-day Refresh Token, bearer type, and user."""
    # Register
    await async_client.post(
        "/api/v1/auth/register",
        json={"email": "login.user@infrascan.gov", "password": "MyLoginPassword123!", "full_name": "Login Tester"},
    )

    # Login
    res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "login.user@infrascan.gov", "password": "MyLoginPassword123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "login.user@infrascan.gov"
    assert "id" in data["user"]
    assert "role" in data["user"]

    # Verify Access Token claims & 15-minute expiry (approx 900 seconds)
    access_claims = decode_access_token(data["access_token"])
    assert access_claims["type"] == "access"
    assert access_claims["exp"] - access_claims["iat"] == 15 * 60

    # Verify Refresh Token claims & 7-day expiry (approx 7*86400 seconds)
    refresh_claims = decode_refresh_token(data["refresh_token"])
    assert refresh_claims["type"] == "refresh"
    assert refresh_claims["exp"] - refresh_claims["iat"] == 7 * 86400


@pytest.mark.asyncio
async def test_login_failure_wrong_password_and_inactive_account(async_client: AsyncClient):
    """Test 401 Unauthorized on incorrect password and inactive account."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "tester.inactive@infrascan.gov", "password": "ValidPassword123!", "full_name": "Inactive User"},
    )
    assert reg.status_code == 201

    # Wrong password -> 401
    bad_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "tester.inactive@infrascan.gov", "password": "WrongPassword999!"},
    )
    assert bad_res.status_code == 401

    # Deactivate user
    async with AsyncTestingSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == "tester.inactive@infrascan.gov"))
        user.is_active = False
        await session.commit()

    # Login with inactive account -> 401
    inactive_res = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "tester.inactive@infrascan.gov", "password": "ValidPassword123!"},
    )
    assert inactive_res.status_code == 401
    assert "deactivated" in inactive_res.json()["detail"].lower() or "inactive" in inactive_res.json()["detail"].lower()


# ============================================================================
# 3. Refresh Token Rotation & Revocation
# ============================================================================

@pytest.mark.asyncio
async def test_refresh_token_rotation_and_old_token_revocation(async_client: AsyncClient):
    """Test that refreshing tokens issues a new pair and revokes the old refresh token."""
    login_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "rotate.test@infrascan.gov", "password": "Password123!", "full_name": "Rotation Test"},
    )
    initial_refresh = login_res.json()["refresh_token"]

    # 1. Use refresh token to get new tokens
    refresh_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    new_refresh = new_tokens["refresh_token"]
    assert new_refresh != initial_refresh

    # 2. Attempting to reuse the old refresh token must be rejected (401)
    reused_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": initial_refresh},
    )
    assert reused_res.status_code == 401


# ============================================================================
# 4. Logout & Token Revocation
# ============================================================================

@pytest.mark.asyncio
async def test_logout_revokes_token(async_client: AsyncClient):
    """Test that logging out revokes the active refresh token."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "logout.user@infrascan.gov", "password": "Password123!", "full_name": "Logout User"},
    )
    access_token = reg.json()["access_token"]
    refresh_token = reg.json()["refresh_token"]

    # Logout
    logout_res = await async_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"refresh_token": refresh_token},
    )
    assert logout_res.status_code == 200

    # Refreshing with the revoked refresh token must now fail
    ref_res = await async_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code == 401


# ============================================================================
# 5. Change Password (Secure Argon2 Update)
# ============================================================================

@pytest.mark.asyncio
async def test_change_password_endpoint(async_client: AsyncClient):
    """Test changing password with current password verification."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "pwd.user@infrascan.gov", "password": "OldPassword123!", "full_name": "Password User"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Wrong current password -> 400
    bad_pwd = await async_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "WrongOldPassword!", "new_password": "NewSuperPassword123!"},
    )
    assert bad_pwd.status_code == 400

    # Correct current password -> 200
    good_pwd = await async_client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "OldPassword123!", "new_password": "NewSuperPassword123!"},
    )
    assert good_pwd.status_code == 200

    # Verify login with new password works
    new_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pwd.user@infrascan.gov", "password": "NewSuperPassword123!"},
    )
    assert new_login.status_code == 200

    # Verify old password no longer works
    old_login = await async_client.post(
        "/api/v1/auth/login",
        json={"email": "pwd.user@infrascan.gov", "password": "OldPassword123!"},
    )
    assert old_login.status_code == 401


# ============================================================================
# 6. Google OAuth2 Login & Security Rule Enforcement
# ============================================================================

@pytest.mark.asyncio
async def test_google_oauth2_flow_and_safe_default_role(async_client: AsyncClient):
    """Test Google OAuth2 callback assigns safe default role (never elevated role)."""
    # 1. Test GET /api/v1/auth/google initiator returns redirect or foundation metadata
    google_init = await async_client.get("/api/v1/auth/google")
    assert google_init.status_code in [200, 302, 307]

    # 2. Test Google OAuth2 callback handler provisions user with safe default role (CIVIL_ENGINEER)
    callback_res = await async_client.get(
        "/api/v1/auth/google/callback",
        params={"mock_email": "google.civilian@infrascan.gov", "mock_name": "Google User"},
    )
    assert callback_res.status_code == 200
    data = callback_res.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # Security Rule: Safe default role assigned, NOT ADMIN or elevated
    assert data["user"]["role"] in ["CIVIL_ENGINEER", "INFRASTRUCTURE_INSPECTOR"]
    assert data["user"]["role"] != "ADMIN"


# ============================================================================
# 7. User Profile Management (GET/PUT /api/v1/users/me)
# ============================================================================

@pytest.mark.asyncio
async def test_user_profile_me_endpoints(async_client: AsyncClient):
    """Test reading and updating user profile."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "profile.me@infrascan.gov", "password": "Password123!", "full_name": "Original Profile Name"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # GET /api/v1/users/me
    get_me = await async_client.get("/api/v1/users/me", headers=headers)
    assert get_me.status_code == 200
    assert get_me.json()["full_name"] == "Original Profile Name"

    # PUT /api/v1/users/me
    put_me = await async_client.put(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "Updated Profile Name"},
    )
    assert put_me.status_code == 200
    assert put_me.json()["full_name"] == "Updated Profile Name"


# ============================================================================
# 8. Admin Management & RBAC Permissions
# ============================================================================

@pytest.mark.asyncio
async def test_admin_management_and_rbac_restrictions(async_client: AsyncClient):
    """Test that Admin endpoints require ADMIN role and reject unauthorized roles with 403."""
    # Register regular Civil Engineer
    user_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "regular.user@infrascan.gov", "password": "Password123!", "role": "CIVIL_ENGINEER"},
    )
    user_token = user_res.json()["access_token"]
    user_id = user_res.json()["user"]["id"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Register Administrator
    admin_res = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "admin.master@infrascan.gov", "password": "AdminPassword123!", "role": "ADMIN"},
    )
    admin_token = admin_res.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. GET /api/v1/admin/users
    # Regular user gets 403 Forbidden
    u_list = await async_client.get("/api/v1/admin/users", headers=user_headers)
    assert u_list.status_code == 403

    # Admin gets 200 OK
    a_list = await async_client.get("/api/v1/admin/users", headers=admin_headers)
    assert a_list.status_code == 200
    assert len(a_list.json()) >= 2

    # 2. PATCH /api/v1/admin/users/{id}/role
    # Regular user gets 403 Forbidden
    u_patch = await async_client.patch(
        f"/api/v1/admin/users/{user_id}/role",
        headers=user_headers,
        json={"role": "MAINTENANCE_ENGINEER"},
    )
    assert u_patch.status_code == 403

    # Admin successfully updates role
    a_patch = await async_client.patch(
        f"/api/v1/admin/users/{user_id}/role",
        headers=admin_headers,
        json={"role": "MAINTENANCE_ENGINEER"},
    )
    assert a_patch.status_code == 200
    assert a_patch.json()["role"] == "MAINTENANCE_ENGINEER"

    # 3. GET /api/v1/admin/audit-logs
    # Regular user gets 403 Forbidden
    u_logs = await async_client.get("/api/v1/admin/audit-logs", headers=user_headers)
    assert u_logs.status_code == 403

    # Admin gets 200 OK
    a_logs = await async_client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert a_logs.status_code == 200
    logs = a_logs.json()
    assert len(logs) > 0
    actions = {item["action"] for item in logs}
    assert "USER_ROLE_UPDATED" in actions or "RBAC_DENIED" in actions


# ============================================================================
# 9. Initial Admin Seeding Script Verification
# ============================================================================

@pytest.mark.asyncio
async def test_seed_admin_script():
    """Verify that seed_admin script creates an active ADMIN user with Argon2 hash."""
    await seed_admin(
        email="seed.admin@infrascan.gov",
        password="SeedAdminSecret123!",
        full_name="Seed Administrator",
        session_factory=AsyncTestingSessionLocal,
    )

    async with AsyncTestingSessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == "seed.admin@infrascan.gov"))
        assert user is not None
        assert user.role == UserRole.ADMIN
        assert user.is_active is True
        assert user.password_hash.startswith("$argon2id$")
        assert verify_password("SeedAdminSecret123!", user.password_hash) is True
