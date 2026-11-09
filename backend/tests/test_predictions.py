import io
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.config import settings
from backend.db.session import Base, get_async_db
from backend.main import app
from backend.models.inspection import Inspection  # noqa: F401
from backend.models.prediction import Prediction  # noqa: F401
from backend.services.ai_inference import AIInferenceService

# Asynchronous test database engine using in-memory SQLite with aiosqlite
TEST_ASYNC_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingAsyncSessionLocal = async_sessionmaker(
    bind=TEST_ASYNC_ENGINE,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def create_test_image_bytes(image_format: str = "JPEG", size: tuple[int, int] = (640, 480)) -> bytes:
    """Generate in-memory byte buffer of a valid test image."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(140, 150, 160))
    img.save(buf, format=image_format)
    return buf.getvalue()


@pytest.fixture()
def client(tmp_path):
    # Temporarily point upload directory to pytest tmp_path
    original_upload_dir = settings.UPLOAD_DIR
    settings.UPLOAD_DIR = str(tmp_path / "uploads")

    # Set up tables synchronously via sync connection wrapper on in-memory engine
    import asyncio

    async def init_models():
        async with TEST_ASYNC_ENGINE.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())

    async def override_get_async_db():
        async with TestingAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_async_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

    async def drop_models():
        async with TEST_ASYNC_ENGINE.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(drop_models())
    settings.UPLOAD_DIR = original_upload_dir


def test_analyze_valid_jpeg_image(client):
    """Test successful image upload, AI analysis, and prediction persistence."""
    image_bytes = create_test_image_bytes(image_format="JPEG")
    files = {"file": ("inspection_pier_north.jpg", image_bytes, "image/jpeg")}
    data = {"asset_id": 1}

    response = client.post("/api/v1/predictions/analyze", data=data, files=files)
    assert response.status_code == 201

    payload = response.json()
    assert payload["id"] is not None
    assert payload["asset_id"] == 1
    assert payload["confidence_score"] > 0.0
    assert payload["confidence_score"] <= 1.0
    assert payload["recommended_action"] != ""
    assert payload["predicted_failure_date"] is not None
    assert payload["severity_level"] != ""
    assert "defect_details" in payload
    assert payload["defect_details"]["total_defects"] >= 1

    # Verify bounding boxes and segmentation masks exist in defect details
    defects = payload["defect_details"]["defects"]
    assert len(defects) > 0
    first_defect = defects[0]
    assert "bounding_box" in first_defect
    assert "segmentation_mask" in first_defect
    assert len(first_defect["segmentation_mask"]["polygon"]) > 3

    # Verify retrieval by prediction ID
    prediction_id = payload["id"]
    get_res = client.get(f"/api/v1/predictions/{prediction_id}")
    assert get_res.status_code == 200
    assert get_res.json()["asset_id"] == 1

    # Verify retrieval by asset ID
    asset_res = client.get("/api/v1/predictions/asset/1")
    assert asset_res.status_code == 200
    assert len(asset_res.json()) == 1


def test_analyze_png_format(client):
    """Test upload with PNG image format."""
    image_bytes = create_test_image_bytes(image_format="PNG")
    files = {"file": ("crack_detail.png", image_bytes, "image/png")}
    data = {"asset_id": 2}

    response = client.post("/api/v1/predictions/analyze", data=data, files=files)
    assert response.status_code == 201
    assert response.json()["asset_id"] == 2


def test_reject_unsupported_media_type(client):
    """Test rejection when uploading non-image format (e.g. text/plain)."""
    fake_doc = b"Hello, this is a text file masquerading as an image."
    files = {"file": ("notes.txt", fake_doc, "text/plain")}
    data = {"asset_id": 1}

    response = client.post("/api/v1/predictions/analyze", data=data, files=files)
    assert response.status_code == 415
    assert "Unsupported image media type" in response.json()["detail"]


def test_reject_corrupt_image(client):
    """Test rejection when image payload bytes are corrupt or not a valid image structure."""
    corrupt_bytes = b"\xff\xd8\xff\xe0" + b"random garbage not a real JPEG image"
    files = {"file": ("corrupt.jpg", corrupt_bytes, "image/jpeg")}
    data = {"asset_id": 1}

    response = client.post("/api/v1/predictions/analyze", data=data, files=files)
    assert response.status_code == 400
    assert "corrupted or not a valid image format" in response.json()["detail"]


def test_reject_empty_file(client):
    """Test rejection of empty uploaded file (0 bytes)."""
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    data = {"asset_id": 1}

    response = client.post("/api/v1/predictions/analyze", data=data, files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"]


def test_reject_blank_or_invalid_asset_id(client):
    """Test rejection when asset_id is invalid string or negative number."""
    image_bytes = create_test_image_bytes(image_format="JPEG")
    files = {"file": ("test.jpg", image_bytes, "image/jpeg")}

    # String that cannot parse as integer
    res1 = client.post("/api/v1/predictions/analyze", data={"asset_id": "not-an-int"}, files=files)
    assert res1.status_code == 422

    # Negative integer
    res2 = client.post("/api/v1/predictions/analyze", data={"asset_id": -5}, files=files)
    assert res2.status_code == 422



def test_get_nonexistent_prediction_returns_404(client):
    """Test fetching nonexistent prediction ID returns 404."""
    response = client.get("/api/v1/predictions/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ai_service_unit_pipeline():
    """Unit test the AI inference service methods directly."""
    service = AIInferenceService()
    assert service.detection_model["status"] == "ready"
    assert service.segmentation_model["status"] == "ready"

    image_bytes = create_test_image_bytes(image_format="JPEG", size=(800, 600))
    result = await service.analyze(image_bytes=image_bytes, filename="test.jpg")

    assert 0.0 <= result.confidence_score <= 1.0
    assert result.severity_level in {
        "Critical / Requires Urgent Engineering Review",
        "Severe Damage",
        "Moderate Damage",
        "Minor Damage",
        "No Visible Damage",
    }
    assert result.recommended_action != ""
    assert result.predicted_failure_date is not None
    assert result.defect_details["total_defects"] == 2
    assert result.defect_details["crack_density_percentage"] > 0


def test_stored_image_persists_on_filesystem(client):
    """Test that uploaded image is physically persisted in the upload directory."""
    image_bytes = create_test_image_bytes(image_format="JPEG")
    files = {"file": ("physical_check.jpg", image_bytes, "image/jpeg")}
    data = {"asset_id": 999}

    res = client.post("/api/v1/predictions/analyze", data=data, files=files)
    assert res.status_code == 201

    saved_path = Path(res.json()["image_path"])
    assert saved_path.exists()
    assert saved_path.stat().st_size == len(image_bytes)


def test_frontend_images_upload_endpoint(client):
    """Test the /images/upload endpoint used by the frontend Upload page."""
    image_bytes = create_test_image_bytes(image_format="JPEG")
    files = [("images", ("flyover_crack.jpg", image_bytes, "image/jpeg"))]
    data = {
        "assetId": "INF-001",
        "date": "2026-11-04",
        "inspector": "Dr. L. Venkat",
        "notes": "Surface crack observed near abutment.",
    }

    res = client.post("/images/upload", data=data, files=files)
    assert res.status_code == 201

    payload = res.json()
    assert payload["status"] == "success"
    assert "Successfully stored" in payload["message"]
    assert payload["count"] == 1
    assert payload["asset_id"] == 1
    assert len(payload["stored_images"]) == 1
    assert len(payload["predictions"]) == 1

    stored_img = payload["stored_images"][0]
    assert Path(stored_img["image_path"]).exists()
    assert stored_img["image_url"].startswith("/uploads/")

    pred = payload["predictions"][0]
    assert pred["severity_level"] != ""
    assert pred["confidence_score"] > 0
    assert pred["recommended_action"] != ""


def test_assets_endpoint(client):
    """Test that /assets returns a list of assets for the frontend dropdown."""
    res = client.get("/assets")
    assert res.status_code == 200
    assets = res.json()
    assert isinstance(assets, list)
    assert len(assets) > 0
    assert "id" in assets[0]
    assert "name" in assets[0]


