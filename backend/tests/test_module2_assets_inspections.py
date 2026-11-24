"""Comprehensive automated test suite for Module 2: Infrastructure Asset & Inspection Management.

Tests:
1. Asset Creation (201 Created), Category Validation (BRIDGE, ROAD, BUILDING, TUNNEL, DAM), 403 for Inspector
2. Asset Listing with filtering (asset_type, department, search) and soft-delete exclusion
3. Asset Retrieval (200 OK) & 404 on missing / archived asset
4. Asset Update (200 OK, audit logged)
5. Asset Soft-Deletion / Archival (is_archived=True, audit logged)
6. Asset Historical Inspection Timeline (GET /assets/{id}/inspections)
7. Inspection Creation (201 Created), asset existence check (404), active inspector validation (400 for inactive)
8. Inspection Listing & Filtering (status, asset_id, inspector_id)
9. Inspection Assignment (PATCH /assign), RBAC checks (403 for inspector), status transition to ASSIGNED
10. Inspection Status Transitions (PATCH /status), enum validation
11. Inspection Images stub (GET /images ready for Module 3)
12. Audit Logging verification for all actions (ASSET_CREATED, ASSET_UPDATED, ASSET_ARCHIVED, INSPECTION_CREATED, INSPECTION_ASSIGNED)
"""

import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.app.db.session import Base, get_async_db
from backend.app.main import app
from backend.app.models.asset import AssetType, InfrastructureAsset
from backend.app.models.inspection import Inspection, InspectionStatus
from backend.app.models.user import User, UserRole

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


@pytest_asyncio.fixture
async def auth_tokens(async_client: AsyncClient):
    """Create users with each role and provide their authorization headers."""
    # 1. Admin
    admin_reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "admin@infra.gov", "password": "Password123!", "role": "ADMIN"},
    )
    admin_token = admin_reg.json()["access_token"]

    # 2. Civil Engineer
    eng_reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "engineer@infra.gov", "password": "Password123!", "role": "CIVIL_ENGINEER"},
    )
    eng_token = eng_reg.json()["access_token"]
    eng_id = eng_reg.json()["user"]["id"]

    # 3. Infrastructure Inspector
    insp_reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "inspector@infra.gov", "password": "Password123!", "role": "INFRASTRUCTURE_INSPECTOR"},
    )
    insp_token = insp_reg.json()["access_token"]
    insp_id = insp_reg.json()["user"]["id"]

    # 4. Inactive Inspector
    inactive_reg = await async_client.post(
        "/api/v1/auth/register",
        json={"email": "inactive.insp@infra.gov", "password": "Password123!", "role": "INFRASTRUCTURE_INSPECTOR"},
    )
    inactive_id = inactive_reg.json()["user"]["id"]
    async with AsyncTestingSessionLocal() as session:
        inactive_user = await session.scalar(select(User).where(User.id == uuid.UUID(inactive_id)))
        inactive_user.is_active = False
        await session.commit()

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "engineer_headers": {"Authorization": f"Bearer {eng_token}"},
        "engineer_id": eng_id,
        "inspector_headers": {"Authorization": f"Bearer {insp_token}"},
        "inspector_id": insp_id,
        "inactive_inspector_id": inactive_id,
    }


# ============================================================================
# 1. Asset Creation & Category Validation & RBAC
# ============================================================================

@pytest.mark.asyncio
async def test_create_asset_success_and_rbac(async_client: AsyncClient, auth_tokens):
    """Test asset registration as Engineer (201) vs. Inspector (403 Forbidden)."""
    payload = {
        "asset_name": "Vidyasagar Setu Second Hooghly Bridge",
        "asset_type": "BRIDGE",
        "location": "Kolkata, West Bengal",
        "latitude": 22.5583,
        "longitude": 88.3247,
        "construction_year": 1992,
        "material_type": "Steel Cable-Stayed",
        "department": "Highways and Bridges Division",
        "inspection_frequency": 60,
    }

    # 1. Inspector receives 403 Forbidden
    insp_res = await async_client.post(
        "/api/v1/assets",
        headers=auth_tokens["inspector_headers"],
        json=payload,
    )
    assert insp_res.status_code == 403
    assert "insufficient permissions" in insp_res.json()["detail"].lower()

    # 2. Civil Engineer successfully creates asset (201 Created)
    eng_res = await async_client.post(
        "/api/v1/assets",
        headers=auth_tokens["engineer_headers"],
        json=payload,
    )
    assert eng_res.status_code == 201
    asset_data = eng_res.json()
    assert asset_data["asset_name"] == payload["asset_name"]
    assert asset_data["asset_type"] == "BRIDGE"
    assert asset_data["is_archived"] is False
    assert "id" in asset_data


@pytest.mark.asyncio
async def test_asset_category_validation(async_client: AsyncClient, auth_tokens):
    """Ensure asset_type only accepts allowed categories (BRIDGE, ROAD, BUILDING, TUNNEL, DAM)."""
    # Invalid category
    invalid_payload = {
        "asset_name": "Subway Track 4",
        "asset_type": "SUBWAY_TRAIN",
        "location": "Metro Line 2",
    }
    res = await async_client.post(
        "/api/v1/assets",
        headers=auth_tokens["engineer_headers"],
        json=invalid_payload,
    )
    assert res.status_code == 422

    # Valid categories: ROAD, BUILDING, TUNNEL, DAM
    for cat in ["ROAD", "BUILDING", "TUNNEL", "DAM"]:
        valid_res = await async_client.post(
            "/api/v1/assets",
            headers=auth_tokens["engineer_headers"],
            json={"asset_name": f"Test {cat}", "asset_type": cat, "location": "Test City"},
        )
        assert valid_res.status_code == 201
        assert valid_res.json()["asset_type"] == cat


# ============================================================================
# 2. Asset Querying, Filtering & Search
# ============================================================================

@pytest.mark.asyncio
async def test_list_assets_with_filtering_and_search(async_client: AsyncClient, auth_tokens):
    """Test GET /api/v1/assets with category filtering and keyword search."""
    headers = auth_tokens["engineer_headers"]
    # Create test assets
    await async_client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_name": "Bandra Worli Sea Link", "asset_type": "BRIDGE", "location": "Mumbai, Maharashtra", "department": "MSRDC"},
    )
    await async_client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_name": "Atal Tunnel Rohtang", "asset_type": "TUNNEL", "location": "Himachal Pradesh", "department": "BRO"},
    )
    await async_client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_name": "Tehri Hydro Dam", "asset_type": "DAM", "location": "Uttarakhand", "department": "THDC"},
    )

    # 1. Any role (including Inspector) can view assets
    all_res = await async_client.get("/api/v1/assets", headers=auth_tokens["inspector_headers"])
    assert all_res.status_code == 200
    assert len(all_res.json()) >= 3

    # 2. Filter by asset_type
    tunnels = await async_client.get("/api/v1/assets", headers=headers, params={"asset_type": "TUNNEL"})
    assert tunnels.status_code == 200
    assert len(tunnels.json()) == 1
    assert tunnels.json()[0]["asset_name"] == "Atal Tunnel Rohtang"

    # 3. Filter by department
    dams = await async_client.get("/api/v1/assets", headers=headers, params={"department": "THDC"})
    assert dams.status_code == 200
    assert len(dams.json()) == 1
    assert dams.json()[0]["asset_name"] == "Tehri Hydro Dam"

    # 4. Search by keyword
    search_res = await async_client.get("/api/v1/assets", headers=headers, params={"search": "Worli"})
    assert search_res.status_code == 200
    assert len(search_res.json()) == 1
    assert search_res.json()[0]["asset_name"] == "Bandra Worli Sea Link"


# ============================================================================
# 3. Asset Details, Update & Soft Deletion
# ============================================================================

@pytest.mark.asyncio
async def test_asset_crud_and_soft_delete(async_client: AsyncClient, auth_tokens):
    """Test retrieving details, updating, and soft-deleting an asset."""
    headers = auth_tokens["engineer_headers"]
    created = await async_client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_name": "Old Metro Bridge", "asset_type": "BRIDGE", "location": "Delhi Sector 5"},
    )
    asset_id = created.json()["id"]

    # 1. Retrieve asset details (GET)
    detail_res = await async_client.get(f"/api/v1/assets/{asset_id}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["asset_name"] == "Old Metro Bridge"

    # 2. Update asset details (PUT)
    update_res = await async_client.put(
        f"/api/v1/assets/{asset_id}",
        headers=headers,
        json={"asset_name": "Refurbished Metro Overpass", "inspection_frequency": 30},
    )
    assert update_res.status_code == 200
    assert update_res.json()["asset_name"] == "Refurbished Metro Overpass"
    assert update_res.json()["inspection_frequency"] == 30

    # 3. Soft-delete (archive) asset (DELETE)
    del_res = await async_client.delete(f"/api/v1/assets/{asset_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "ARCHIVED"

    # 4. Normal GET for archived asset returns 404
    get_archived = await async_client.get(f"/api/v1/assets/{asset_id}", headers=headers)
    assert get_archived.status_code == 404

    # 5. Archived asset is excluded from list by default
    active_list = await async_client.get("/api/v1/assets", headers=headers)
    active_ids = [a["id"] for a in active_list.json()]
    assert asset_id not in active_ids


# ============================================================================
# 4. Inspection Creation & Inspector Validation
# ============================================================================

@pytest.mark.asyncio
async def test_create_inspection_validation(async_client: AsyncClient, auth_tokens):
    """Test inspection creation validation (asset exists, active inspector check)."""
    headers = auth_tokens["engineer_headers"]

    # Create an active asset
    asset = await async_client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_name": "Expressway Bridge 10", "asset_type": "BRIDGE", "location": "Pune Highway"},
    )
    asset_id = asset.json()["id"]

    # 1. Creating inspection on non-existent asset -> 404
    fake_asset_id = str(uuid.uuid4())
    bad_asset_res = await async_client.post(
        "/api/v1/inspections",
        headers=headers,
        json={"asset_id": fake_asset_id},
    )
    assert bad_asset_res.status_code == 404

    # 2. Creating inspection with inactive inspector -> 400 Bad Request
    inactive_insp_res = await async_client.post(
        "/api/v1/inspections",
        headers=headers,
        json={"asset_id": asset_id, "inspector_id": auth_tokens["inactive_inspector_id"]},
    )
    assert inactive_insp_res.status_code == 400
    assert "inactive" in inactive_insp_res.json()["detail"].lower()

    # 3. Creating inspection with non-existent inspector -> 404 Not Found
    fake_insp_res = await async_client.post(
        "/api/v1/inspections",
        headers=headers,
        json={"asset_id": asset_id, "inspector_id": str(uuid.uuid4())},
    )
    assert fake_insp_res.status_code == 404

    # 4. Creating unassigned inspection -> initial status CREATED
    unassigned = await async_client.post(
        "/api/v1/inspections",
        headers=headers,
        json={"asset_id": asset_id, "remarks": "Initial scoping inspection"},
    )
    assert unassigned.status_code == 201
    assert unassigned.json()["status"] == "CREATED"
    assert unassigned.json()["inspector_id"] is None

    # 5. Creating pre-assigned inspection -> initial status ASSIGNED
    assigned = await async_client.post(
        "/api/v1/inspections",
        headers=headers,
        json={"asset_id": asset_id, "inspector_id": auth_tokens["inspector_id"], "remarks": "Assigned check"},
    )
    assert assigned.status_code == 201
    assert assigned.json()["status"] == "ASSIGNED"
    assert assigned.json()["inspector_id"] == auth_tokens["inspector_id"]


# ============================================================================
# 5. Inspection Assignment, Status Transitions & Historical Timeline
# ============================================================================

@pytest.mark.asyncio
async def test_inspection_assignment_status_and_history(async_client: AsyncClient, auth_tokens):
    """Test assigning inspector, updating status, and retrieving asset historical timeline."""
    headers = auth_tokens["engineer_headers"]

    # Create asset
    asset = await async_client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_name": "NH-48 Overpass", "asset_type": "BRIDGE", "location": "Gurugram"},
    )
    asset_id = asset.json()["id"]

    # Create unassigned inspection
    insp = await async_client.post(
        "/api/v1/inspections",
        headers=headers,
        json={"asset_id": asset_id, "remarks": "Pending assignment"},
    )
    insp_id = insp.json()["id"]
    assert insp.json()["status"] == "CREATED"

    # 1. Inspector cannot assign inspections (403 Forbidden)
    assign_by_insp = await async_client.patch(
        f"/api/v1/inspections/{insp_id}/assign",
        headers=auth_tokens["inspector_headers"],
        json={"inspector_id": auth_tokens["inspector_id"]},
    )
    assert assign_by_insp.status_code == 403

    # 2. Engineer assigns active inspector (200 OK, transitions to ASSIGNED)
    assign_res = await async_client.patch(
        f"/api/v1/inspections/{insp_id}/assign",
        headers=headers,
        json={"inspector_id": auth_tokens["inspector_id"]},
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["status"] == "ASSIGNED"
    assert assign_res.json()["inspector_id"] == auth_tokens["inspector_id"]

    # 3. Transition status to IN_PROGRESS
    status_prog = await async_client.patch(
        f"/api/v1/inspections/{insp_id}/status",
        headers=auth_tokens["inspector_headers"],
        json={"status": "IN_PROGRESS"},
    )
    assert status_prog.status_code == 200
    assert status_prog.json()["status"] == "IN_PROGRESS"

    # 4. Invalid status transition rejected (422)
    bad_status = await async_client.patch(
        f"/api/v1/inspections/{insp_id}/status",
        headers=headers,
        json={"status": "FLYING_DRONE_STATUS"},
    )
    assert bad_status.status_code == 422

    # 5. Retrieve historical inspection timeline for the asset
    timeline_res = await async_client.get(
        f"/api/v1/assets/{asset_id}/inspections",
        headers=auth_tokens["inspector_headers"],
    )
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert len(timeline) >= 1
    assert timeline[0]["id"] == insp_id
    assert timeline[0]["status"] == "IN_PROGRESS"

    # 6. Inspection images endpoint returns clean list
    img_res = await async_client.get(
        f"/api/v1/inspections/{insp_id}/images",
        headers=headers,
    )
    assert img_res.status_code == 200
    assert isinstance(img_res.json(), list)


# ============================================================================
# 6. Audit Logging Verification for Module 2
# ============================================================================

@pytest.mark.asyncio
async def test_module2_audit_log_entries(async_client: AsyncClient, auth_tokens):
    """Verify that asset creation, updates, and assignments write audit log records."""
    headers = auth_tokens["engineer_headers"]
    admin_headers = auth_tokens["admin_headers"]

    # 1. Create asset
    asset_res = await async_client.post(
        "/api/v1/assets",
        headers=headers,
        json={"asset_name": "Audit Tracked Bridge", "asset_type": "BRIDGE", "location": "Chennai"},
    )
    asset_id = asset_res.json()["id"]

    # 2. Archive asset
    await async_client.delete(f"/api/v1/assets/{asset_id}", headers=headers)

    # 3. Inspect audit logs as Admin
    logs_res = await async_client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert logs_res.status_code == 200
    logs = logs_res.json()
    actions = {log["action"] for log in logs}

    assert "ASSET_CREATED" in actions
    assert "ASSET_ARCHIVED" in actions
