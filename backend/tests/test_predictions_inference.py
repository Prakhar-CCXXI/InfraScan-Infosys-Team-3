"""Backend tests for the real-inference integration.

* test_road_scene_real_models_no_mock_with_hashes FAILS if the prediction is mock data, lacks
  SHA-256 model hashes, or is missing the D00/D40 detections on India_000005.jpg.
  It needs the real checkpoints; set SKIP_REAL_MODEL_TESTS=1 only on machines without them.
* The 503 tests need no checkpoints (they point the settings at files that do not exist).
"""
import asyncio
import io
import os
import re
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.config import REPO_ROOT, Settings, settings
from backend.db.session import Base, get_async_db
from backend.main import app
from backend.models.prediction import Prediction  # noqa: F401
from backend.services.ai_inference import reset_ai_inference_service

REAL_IMAGE = REPO_ROOT / "data" / "rdd2022_yolo" / "images" / "test" / "India_000005.jpg"
RDD_CLASSES = {"D00", "D10", "D20", "D40"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")

TEST_ASYNC_ENGINE = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingAsyncSessionLocal = async_sessionmaker(
    bind=TEST_ASYNC_ENGINE, class_=AsyncSession, autoflush=False, autocommit=False, expire_on_commit=False
)


def noise_jpeg(size=(640, 480)) -> bytes:
    arr = np.random.default_rng(0).integers(0, 255, (size[1], size[0], 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG")
    return buf.getvalue()


def _client_ctx(tmp_path):
    """TestClient over an in-memory DB, fresh InferenceService singleton, tmp upload dir."""
    settings.UPLOAD_DIR = str(tmp_path / "uploads")
    reset_ai_inference_service()

    async def init_models():
        async with TEST_ASYNC_ENGINE.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init_models())

    async def override_get_async_db():
        async with TestingAsyncSessionLocal() as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_async_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()

        async def drop_models():
            async with TEST_ASYNC_ENGINE.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        asyncio.run(drop_models())
        reset_ai_inference_service()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", settings.UPLOAD_DIR)  # restored on teardown
    monkeypatch.setattr(settings, "ALLOW_MOCK_INFERENCE", False)
    yield from _client_ctx(tmp_path)


@pytest.fixture()
def missing_models_client(tmp_path, monkeypatch):
    """Checkpoints point at files that do not exist; mock output NOT allowed."""
    monkeypatch.setattr(settings, "UPLOAD_DIR", settings.UPLOAD_DIR)
    monkeypatch.setattr(settings, "UNET_CKPT", str(tmp_path / "missing_unet.pt"))
    monkeypatch.setattr(settings, "RDD_CKPT", str(tmp_path / "missing_rdd.pt"))
    monkeypatch.setattr(settings, "CRACK_YOLO_CKPT", None)
    monkeypatch.setattr(settings, "ALLOW_MOCK_INFERENCE", False)
    yield from _client_ctx(tmp_path)


@pytest.fixture()
def mock_allowed_client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", settings.UPLOAD_DIR)
    monkeypatch.setattr(settings, "UNET_CKPT", str(tmp_path / "missing_unet.pt"))
    monkeypatch.setattr(settings, "RDD_CKPT", str(tmp_path / "missing_rdd.pt"))
    monkeypatch.setattr(settings, "CRACK_YOLO_CKPT", None)
    monkeypatch.setattr(settings, "ALLOW_MOCK_INFERENCE", True)
    yield from _client_ctx(tmp_path)


# --------------------------------------------------------------------------- real models
@pytest.mark.skipif(os.environ.get("SKIP_REAL_MODEL_TESTS") == "1", reason="SKIP_REAL_MODEL_TESTS=1")
def test_road_scene_real_models_no_mock_with_hashes(client):
    assert REAL_IMAGE.is_file(), f"test image missing: {REAL_IMAGE}"
    rdd = settings.resolve_path(settings.RDD_CKPT)
    assert rdd and Path(rdd).is_file(), f"RDD2022 checkpoint missing: {rdd}"

    res = client.post(
        "/api/v1/predictions/analyze",
        data={"asset_id": 1, "profile": "road_scene"},
        files={"file": (REAL_IMAGE.name, REAL_IMAGE.read_bytes(), "image/jpeg")},
    )
    assert res.status_code == 201, res.text
    p = res.json()
    d = p["defect_details"]

    # never mock, never fabricated
    assert d["source"] == "model", "prediction did not come from the real model"
    assert "MOCK_INFERENCE" not in d["warnings"]
    assert d["profile"] == "road_scene"
    assert p["predicted_failure_date"] is None
    assert d["crack_density_percentage"] is None          # close_up only

    # traceability: every model carries a real SHA-256, raw result is stored
    raw = d["raw_inference"]
    assert raw and raw["profile"] == "road_scene" and raw["status"] == "ok"
    assert raw["models"], "no model references recorded"
    for m in raw["models"]:
        assert m["sha256"] and HEX64.match(m["sha256"]), f"model {m.get('id')} has no valid sha256"
    assert d["models"] == raw["models"]
    assert raw["pipeline"]["config"]["conf"] == pytest.approx(0.233)
    assert "UNVALIDATED_OPERATING_POINT" not in d["warnings"]

    # real RDD2022 classes (smoke-test reference: D00=1, D40=2)
    counts = d["class_counts"]
    assert set(counts) == RDD_CLASSES
    assert counts["D00"] >= 1 and counts["D40"] >= 1, counts
    assert d["total_defects"] == sum(counts.values()) == len(d["defects"])
    for defect in d["defects"]:
        bb = defect["bounding_box"]
        assert bb["class_name"] in RDD_CLASSES
        assert bb["x_max"] > bb["x_min"] and bb["y_max"] > bb["y_min"]
        assert defect["segmentation_mask"] is None           # road_scene returns boxes only
        assert "spall" not in defect["defect_type"].lower()

    # overlay really written under UPLOAD_DIR
    overlay = Path(settings.UPLOAD_DIR) / Path(d["artifacts"]["overlay_uri"]).name
    assert overlay.is_file() and overlay.stat().st_size > 0


# --------------------------------------------------------------------------- 503 behaviour
@pytest.mark.parametrize("profile", ["road_scene", "close_up"])
def test_missing_models_return_503_and_persist_nothing(missing_models_client, profile):
    c = missing_models_client
    res = c.post(
        "/api/v1/predictions/analyze",
        data={"asset_id": 1, "profile": profile},
        files={"file": ("noise.jpg", noise_jpeg(), "image/jpeg")},
    )
    assert res.status_code == 503, res.text
    detail = res.json()["detail"]
    assert detail["status"] == "error"
    assert detail["error"]["code"] == "MODEL_UNAVAILABLE"

    assert c.get("/api/v1/predictions/asset/1").json() == []           # no fabricated row
    upload_dir = Path(settings.UPLOAD_DIR)
    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []  # no orphan files


def test_models_health_reports_unavailable(missing_models_client):
    res = missing_models_client.get("/health/models")
    assert res.status_code == 503
    assert res.json()["profiles"] == {"close_up": False, "road_scene": False}


# --------------------------------------------------------------------------- mock flag
def test_mock_is_off_by_default(monkeypatch):
    for name in ("ALLOW_MOCK_INFERENCE",):
        monkeypatch.delenv(name, raising=False)
    assert Settings(_env_file=None).ALLOW_MOCK_INFERENCE is False


def test_mock_only_with_explicit_flag_and_always_tagged(mock_allowed_client):
    res = mock_allowed_client.post(
        "/api/v1/predictions/analyze",
        data={"asset_id": 1, "profile": "road_scene"},
        files={"file": ("noise.jpg", noise_jpeg(), "image/jpeg")},
    )
    assert res.status_code == 201, res.text
    p = res.json()
    d = p["defect_details"]
    assert d["source"] == "mock"
    assert "MOCK_INFERENCE" in d["warnings"]
    assert p["recommended_action"].startswith("[MOCK")
    assert p["predicted_failure_date"] is None
    assert d["raw_inference"] is None and d["models"] == []


def test_invalid_profile_rejected(client):
    res = client.post(
        "/api/v1/predictions/analyze",
        data={"asset_id": 1, "profile": "satellite"},
        files={"file": ("noise.jpg", noise_jpeg(), "image/jpeg")},
    )
    assert res.status_code == 422
