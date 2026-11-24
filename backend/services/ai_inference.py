"""Adapter between the FastAPI backend and data/ml/service/inference_service.py.

Design rules
------------
* The real ``InferenceService`` is the ONLY source of predictions.
* No silent mock fallback. If models are unavailable the adapter raises
  ``InferenceUnavailableError`` (HTTP 503, code MODEL_UNAVAILABLE). Mock output is
  produced only when ``settings.ALLOW_MOCK_INFERENCE`` is true, and is always tagged
  ``source="mock"`` with a ``MOCK_INFERENCE`` warning.
* Nothing is fabricated: ``predicted_failure_date`` is always None, RDD2022 classes keep
  their real meaning, ``crack_density_percentage`` exists for ``close_up`` only.
* Blocking PyTorch/YOLO work runs in a worker thread (``asyncio.to_thread``).
* ``data/ml`` is imported by file path, so no PYTHONPATH changes are needed.

Coordinates: every box/polygon in ``defect_details`` is in ORIGINAL-image pixels
(processed-frame coordinates divided by ``resize_scale_to_original``). The raw
``raw_inference`` block keeps the processed-frame values untouched.
"""
from __future__ import annotations

import asyncio
import importlib.util
import io
import logging
import sys
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from backend.core.config import REPO_ROOT, settings

logger = logging.getLogger(__name__)

ML_SERVICE_FILE = REPO_ROOT / "data" / "ml" / "service" / "inference_service.py"
_ML_MODULE_NAME = "infrascan_ml_inference_service"
ERROR_SCHEMA_VERSION = "infrascan-inference-0.1"

# Severity vocabulary the frontend already understands
SEVERITY_CRITICAL = "Critical / Requires Urgent Engineering Review"
SEVERITY_SEVERE = "Severe Damage"
SEVERITY_MODERATE = "Moderate Damage"
SEVERITY_MINOR = "Minor Damage"
SEVERITY_NO_DAMAGE = "No Visible Damage"
SEVERITY_UNRATED = "Unrated"

RDD_LABELS = {
    "D00": "Longitudinal Crack",
    "D10": "Transverse Crack",
    "D20": "Alligator Crack",
    "D40": "Other Corruption (incl. Pothole)",
}

MAX_COMPONENTS = 25        # close_up: max crack components returned as "defects"
MIN_COMPONENT_PX = 15      # close_up: ignore specks smaller than this (processed px)
POLYGON_EPSILON_PX = 1.5   # close_up: polygon simplification tolerance

_ADVICE = {
    SEVERITY_CRITICAL: "CRITICAL (advisory): arrange an urgent inspection by a qualified engineer and consider restricting load/access until it is assessed.",
    SEVERITY_SEVERE: "HIGH PRIORITY (advisory): schedule a qualified engineering inspection soon and plan repair; monitor the damage until then.",
    SEVERITY_MODERATE: "MEDIUM PRIORITY (advisory): plan a follow-up inspection and maintenance (e.g. sealing) in the next maintenance cycle.",
    SEVERITY_MINOR: "ROUTINE (advisory): note for the regular maintenance cycle and re-check at the next scheduled inspection.",
    SEVERITY_NO_DAMAGE: "No damage detected by the automated screening. Continue the regular inspection schedule.",
    SEVERITY_UNRATED: "Automated screening result without a severity rating. Review the detections manually.",
}
_ADVICE_SUFFIX = " Automated screening only; requires qualified engineering review."


# --------------------------------------------------------------------------- errors
class InferenceUnavailableError(Exception):
    """Same interface as the ML package's ServiceError (.code .message .http_status .to_dict())."""

    def __init__(self, message: str, code: str = "MODEL_UNAVAILABLE", http_status: int = 503):
        super().__init__(message)
        self.code, self.message, self.http_status = code, message, http_status

    def to_dict(self) -> dict:
        return {"status": "error", "schema_version": ERROR_SCHEMA_VERSION,
                "error": {"code": self.code, "message": self.message}}


def _is_unavailable(exc: BaseException) -> bool:
    return getattr(exc, "http_status", None) == 503 or getattr(exc, "code", None) == "MODEL_UNAVAILABLE"


# --------------------------------------------------------------------------- ML import
_ml_module = None
_ml_import_lock = threading.Lock()


def _ensure_ml_sys_path() -> None:
    """Ensure backend/services, data/ml/*, and training_scripts are importable without PYTHONPATH."""
    candidates = [
        REPO_ROOT / "backend" / "services",
        REPO_ROOT / "data" / "ml",
        REPO_ROOT / "data" / "ml" / "service",
        REPO_ROOT / "data" / "ml" / "hybrid",
        REPO_ROOT / "data" / "ml" / "severity",
        REPO_ROOT / "data" / "ml" / "preprocessing",
        REPO_ROOT / "data" / "ml" / "explain",
        REPO_ROOT / "data" / "Crack500-YOLO-Segmentation" / "training_scripts",
    ]
    for folder in candidates:
        folder_str = str(folder)
        if folder.is_dir() and folder_str not in sys.path:
            sys.path.insert(0, folder_str)


def _load_ml_module():
    """Import data/ml/service/inference_service.py by path after registering sibling ML folders."""
    global _ml_module
    with _ml_import_lock:
        if _ml_module is None:
            if not ML_SERVICE_FILE.is_file():
                raise InferenceUnavailableError(f"ML service module not found: {ML_SERVICE_FILE}")
            _ensure_ml_sys_path()
            spec = importlib.util.spec_from_file_location(_ML_MODULE_NAME, ML_SERVICE_FILE)
            module = importlib.util.module_from_spec(spec)
            sys.modules[_ML_MODULE_NAME] = module
            try:
                spec.loader.exec_module(module)
            except Exception as exc:  # missing torch / ultralytics / cv2 ...
                sys.modules.pop(_ML_MODULE_NAME, None)
                raise InferenceUnavailableError(f"ML package failed to import: {type(exc).__name__}: {exc}") from exc
            _ml_module = module
    return _ml_module

def _build_service_config(mod):
    r = settings.resolve_path
    return mod.ServiceConfig(
        unet_ckpt=r(settings.UNET_CKPT),
        yolo_ckpt=r(settings.CRACK_YOLO_CKPT),
        rdd_ckpt=r(settings.RDD_CKPT),
        cls_ckpt=None,
        hybrid_config=r(settings.HYBRID_CONFIG),
        severity_config=r(settings.SEVERITY_CONFIG),
        registry=r(settings.MODEL_REGISTRY_PATH),
        device=settings.INFERENCE_DEVICE or None,
        verify_hashes=settings.VERIFY_MODEL_HASHES,
    )


# --------------------------------------------------------------------------- output
@dataclass
class AIInferenceOutput:
    """Unified result consumed by the route (same fields as before + artifact bytes)."""

    confidence_score: float
    severity_level: str
    recommended_action: str
    predicted_failure_date: datetime | None
    defect_summary: str
    defect_details: dict[str, Any]
    artifacts: dict[str, bytes] = field(default_factory=dict)  # filename -> bytes, written by the route under UPLOAD_DIR


# --------------------------------------------------------------------------- helpers
def _extract_severity_label(sev: Any, depth: int = 0) -> str | None:
    if not isinstance(sev, dict) or depth > 2:
        return None
    for key in ("level", "severity_level", "label", "rating", "category", "grade", "class"):
        v = sev.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    for v in sev.values():
        found = _extract_severity_label(v, depth + 1)
        if found:
            return found
    return None


def _normalize_severity(label: str | None) -> str:
    if not label:
        return SEVERITY_UNRATED
    l = label.strip().lower().replace("_", " ")
    if "critical" in l or "urgent" in l:
        return SEVERITY_CRITICAL
    if "severe" in l or l in {"high", "major"}:
        return SEVERITY_SEVERE
    if "moderate" in l or l in {"medium", "mid"}:
        return SEVERITY_MODERATE
    if "minor" in l or l in {"low", "slight"}:
        return SEVERITY_MINOR
    if l in {"none", "no damage", "no visible damage", "negligible", "no defect"}:
        return SEVERITY_NO_DAMAGE
    return label.strip()


def _advice_for(severity: str) -> str:
    return _ADVICE.get(severity, _ADVICE[SEVERITY_UNRATED]) + _ADVICE_SUFFIX


def _inv_scale(raw: dict) -> float:
    s = (raw.get("coordinate_frame") or {}).get("resize_scale_to_original") or 1.0
    return 1.0 / float(s) if float(s) > 0 else 1.0


def _original_frame(raw: dict, inv: float) -> dict:
    cf = raw["coordinate_frame"]
    return {
        "width": int(round(cf["width"] * inv)), "height": int(round(cf["height"] * inv)),
        "units": "original_image_px", "origin": "top-left, x right, y down",
        "processed_width": cf["width"], "processed_height": cf["height"], "scale_to_original": round(inv, 6),
    }


def _road_defects(raw: dict, inv: float, severity: str) -> list[dict]:
    defects = []
    for i, d in enumerate(raw.get("detections", []), start=1):
        x0, y0, x1, y1 = [round(float(v) * inv, 1) for v in d["box_xyxy"]]
        code = d["class"]
        defects.append({
            "id": i, "defect_type": RDD_LABELS.get(code, code), "severity": severity,
            "bounding_box": {"x_min": x0, "y_min": y0, "x_max": x1, "y_max": y1,
                             "class_name": code, "confidence": float(d["confidence"])},
            "segmentation_mask": None,
        })
    return defects


def _closeup_defects(mask_png: bytes | None, inv: float, severity: str) -> list[dict]:
    """Connected crack components of the U-Net mask -> box + simplified polygon (original px)."""
    if not mask_png:
        return []
    arr = cv2.imdecode(np.frombuffer(mask_png, np.uint8), cv2.IMREAD_GRAYSCALE)
    if arr is None:
        return []
    n, labels, stats, _ = cv2.connectedComponentsWithStats((arr > 127).astype(np.uint8), connectivity=8)
    order = sorted(range(1, n), key=lambda i: -int(stats[i, cv2.CC_STAT_AREA]))
    defects: list[dict] = []
    for i in order[:MAX_COMPONENTS]:
        x, y, w, h, area = [int(v) for v in stats[i]]
        if area < MIN_COMPONENT_PX:
            break
        crop = (labels[y:y + h, x:x + w] == i).astype(np.uint8)
        contours, _ = cv2.findContours(crop, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        pts = None
        if contours:
            c = cv2.approxPolyDP(max(contours, key=len), POLYGON_EPSILON_PX, True).reshape(-1, 2)
            if len(c) >= 3:
                pts = [[px + x, py + y] for px, py in c.tolist()]
        if pts is None:  # degenerate (1-px line): fall back to the component's box
            pts = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
        defects.append({
            "id": len(defects) + 1, "defect_type": "Crack", "severity": severity,
            "bounding_box": {"x_min": round(x * inv, 1), "y_min": round(y * inv, 1),
                             "x_max": round((x + w) * inv, 1), "y_max": round((y + h) * inv, 1),
                             "class_name": "crack", "confidence": None},
            "segmentation_mask": {"polygon": [[round(px * inv, 1), round(py * inv, 1)] for px, py in pts],
                                  "area_pixels": round(area * inv * inv, 1),
                                  "estimated_length_px": None, "estimated_width_px": None, "mask_confidence": None},
        })
    return defects


# --------------------------------------------------------------------------- service
class AIInferenceService:
    """Backend-facing adapter around the shared ``InferenceService`` singleton."""

    def __init__(self) -> None:
        self._svc = None
        self._init_lock = threading.Lock()
        self.startup_error: str | None = None

    # -- lifecycle ---------------------------------------------------------
    def _get_service(self):
        if self._svc is None:
            with self._init_lock:
                if self._svc is None:
                    mod = _load_ml_module()
                    try:
                        self._svc = mod.InferenceService(_build_service_config(mod))
                    except Exception as exc:
                        if hasattr(exc, "http_status") and hasattr(exc, "to_dict"):
                            raise
                        raise InferenceUnavailableError(f"InferenceService failed to start: {type(exc).__name__}: {exc}") from exc
        return self._svc

    def initialise(self) -> bool:
        """Blocking; called once at startup in a worker thread. Never raises."""
        try:
            self._get_service()
            self.startup_error = None
            return True
        except Exception as exc:
            self.startup_error = getattr(exc, "message", None) or f"{type(exc).__name__}: {exc}"
            logger.error("InferenceService init failed: %s", self.startup_error)
            return False

    def health(self) -> dict[str, Any]:
        """Cheap readiness report. 'ready' = checkpoint files exist; hashes are verified on first use."""
        r = settings.resolve_path

        def ck(path):
            p = r(path)
            return {"path": p, "exists": bool(p and Path(p).is_file())}

        ckpts = {"unet": ck(settings.UNET_CKPT), "rdd2022_yolo11s": ck(settings.RDD_CKPT)}
        if settings.CRACK_YOLO_CKPT:
            ckpts["crack_yolo"] = ck(settings.CRACK_YOLO_CKPT)
        ctx_ok = self.startup_error is None and ML_SERVICE_FILE.is_file()
        profiles = {
            "close_up": ctx_ok and ckpts["unet"]["exists"] and ckpts.get("crack_yolo", {"exists": True})["exists"],
            "road_scene": ctx_ok and ckpts["rdd2022_yolo11s"]["exists"],
        }
        info: dict[str, Any] = {
            "status": "ok" if all(profiles.values()) else ("degraded" if any(profiles.values()) else "unavailable"),
            "service_initialised": self._svc is not None, "startup_error": self.startup_error,
            "mock_allowed": settings.ALLOW_MOCK_INFERENCE, "verify_hashes": settings.VERIFY_MODEL_HASHES,
            "profiles": profiles, "checkpoints": ckpts,
        }
        if self._svc is not None:
            info["service"] = self._svc.health()
        return info

    # -- public API --------------------------------------------------------
    async def analyze(
        self,
        image_bytes: bytes,
        filename: str | None = None,
        *,
        content_type: str | None = None,
        profile: str | None = None,
        artifact_stem: str | None = None,
    ) -> AIInferenceOutput:
        profile = profile or settings.DEFAULT_INFERENCE_PROFILE
        try:
            return await asyncio.to_thread(self._analyze_blocking, image_bytes, content_type, profile, artifact_stem)
        except Exception as exc:
            if settings.ALLOW_MOCK_INFERENCE and _is_unavailable(exc):
                logger.warning("Real models unavailable (%s); returning TAGGED MOCK output (ALLOW_MOCK_INFERENCE=1)", exc)
                return self._mock_output(image_bytes, profile)
            raise

    # -- blocking part (worker thread) ---------------------------------------
    def _analyze_blocking(self, image_bytes, content_type, profile, artifact_stem) -> AIInferenceOutput:
        svc = self._get_service()
        out = svc.analyze(image_bytes, content_type, profile=profile)   # raises ImageValidationError / ServiceError
        return self._adapt(out, profile, artifact_stem)

    def _adapt(self, out, profile: str, stem: str | None) -> AIInferenceOutput:
        raw: dict = out.result
        inv = _inv_scale(raw)

        # artifacts: bytes are returned to the route, which writes them under UPLOAD_DIR
        artifacts: dict[str, bytes] = {}
        uris: dict[str, str | None] = {"mask_uri": None, "overlay_uri": None}
        if stem and out.mask_png:
            artifacts[f"{stem}_mask.png"] = out.mask_png
            uris["mask_uri"] = f"/uploads/{stem}_mask.png"
        if stem and out.overlay_jpg:
            artifacts[f"{stem}_overlay.jpg"] = out.overlay_jpg
            uris["overlay_uri"] = f"/uploads/{stem}_overlay.jpg"
        if profile == "close_up":  # the close_up schema has mask/overlay uri slots for the backend to fill
            if isinstance(raw.get("mask"), dict):
                raw["mask"]["uri"] = uris["mask_uri"]
            if isinstance(raw.get("overlay"), dict):
                raw["overlay"]["uri"] = uris["overlay_uri"]

        severity = _normalize_severity(_extract_severity_label(raw.get("severity")))
        dets = raw.get("detections", [])
        if dets:
            confidence, basis = round(max(float(d["confidence"]) for d in dets), 4), "max_detection_confidence"
        else:
            confidence, basis = 0.0, "not_available"

        if profile == "road_scene":
            defects = _road_defects(raw, inv, severity)
            density = None
            counts = raw.get("class_counts") or {}
            found = [f"{n}x {c} ({RDD_LABELS.get(c, c)})" for c, n in counts.items() if n]
            conf = (raw.get("pipeline") or {}).get("config", {}).get("conf")
            summary = (f"Detected {len(defects)} road-surface defect(s): {', '.join(found)}." if defects
                       else f"No road-surface defects detected at confidence >= {conf}.")
        else:
            defects = _closeup_defects(out.mask_png, inv, severity)
            meas = raw.get("measurements") or {}
            density = meas.get("crack_density_percent")
            summary = (f"Crack mask covers {density}% of the image across {len(defects)} crack component(s)." if defects
                       else "No cracks segmented in the image.")

        details = {
            "source": "model", "profile": profile, "total_defects": len(defects), "severity_level": severity,
            "crack_density_percentage": density, "defects": defects, "summary": summary,
            "confidence_basis": basis, "class_counts": raw.get("class_counts"), "measurements": raw.get("measurements"),
            "warnings": list(raw.get("warnings", [])), "models": raw.get("models"),
            "coordinate_frame": _original_frame(raw, inv), "artifacts": uris,
            "severity_assessment": raw.get("severity"), "preprocessing": out.preprocessing, "raw_inference": raw,
        }
        return AIInferenceOutput(confidence, severity, _advice_for(severity), None, summary, details, artifacts)

    # -- explicit, tagged mock (only when ALLOW_MOCK_INFERENCE=1) ------------
    def _mock_output(self, image_bytes: bytes, profile: str) -> AIInferenceOutput:
        try:
            with Image.open(io.BytesIO(image_bytes)) as im:
                w, h = im.size
        except Exception:
            w, h = 640, 480
        summary = "[MOCK DATA - NOT A REAL PREDICTION] Models unavailable; placeholder output."
        defect = {"id": 1, "defect_type": "MOCK", "severity": SEVERITY_UNRATED,
                  "bounding_box": {"x_min": round(w * .2, 1), "y_min": round(h * .2, 1), "x_max": round(w * .6, 1),
                                   "y_max": round(h * .6, 1), "class_name": "mock", "confidence": None},
                  "segmentation_mask": None}
        details = {
            "source": "mock", "profile": profile, "total_defects": 1, "severity_level": SEVERITY_UNRATED,
            "crack_density_percentage": None, "defects": [defect], "summary": summary, "confidence_basis": "mock",
            "class_counts": None, "measurements": None, "warnings": ["MOCK_INFERENCE"], "models": [],
            "coordinate_frame": {"width": w, "height": h, "units": "original_image_px"},
            "artifacts": {"mask_uri": None, "overlay_uri": None}, "severity_assessment": None,
            "preprocessing": None, "raw_inference": None,
        }
        return AIInferenceOutput(0.0, SEVERITY_UNRATED, "[MOCK DATA] Do not use for any decision.", None, summary, details)


# --------------------------------------------------------------------------- singleton
_ai_service_instance: AIInferenceService | None = None
_singleton_lock = threading.Lock()


def get_ai_inference_service() -> AIInferenceService:
    """FastAPI dependency / accessor for the one shared adapter (creating it is cheap; no ML import)."""
    global _ai_service_instance
    if _ai_service_instance is None:
        with _singleton_lock:
            if _ai_service_instance is None:
                _ai_service_instance = AIInferenceService()
    return _ai_service_instance


def reset_ai_inference_service() -> None:
    """Drop the singleton so the next access rebuilds it from the current settings (tests)."""
    global _ai_service_instance
    with _singleton_lock:
        _ai_service_instance = None
