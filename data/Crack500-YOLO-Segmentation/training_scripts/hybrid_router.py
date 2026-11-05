"""
Optional hybrid (YOLO + U-Net) endpoint for the existing InfraScan FastAPI demo.
Existing routes (/health, /, /api/images, ...) are NOT modified. If weights or dependencies are missing,
this router returns HTTP 503 on its own routes only; the rest of the app keeps working.

Configuration (environment variables):
  INFRASCAN_YOLO_CKPT      path to YOLO11n-Seg best.pt trained on Crack500
  INFRASCAN_UNET_CKPT      path to unet_resnet34_s42/best.pt
  INFRASCAN_HYBRID_CONFIG  path to hybrid_config.json (from evaluate_hybrid.py --stage tune)
  INFRASCAN_HYBRID_KEY     "roi_gated" (default) or "dual_threshold"
  INFRASCAN_MODEL_VERSION  free-text version tag stored in the response (default "hybrid-v0.1")
"""
import os
import sys
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml" / "hybrid"))     # makes hybrid_pipeline / geometry importable

OUT_DIR = ROOT / "uploads" / "hybrid"
OUT_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 10 * 1024 * 1024
MAX_SIDE = 1280
router = APIRouter(prefix="/api/hybrid", tags=["hybrid"])
_pipe = {"obj": None, "cfg": None}


def _get_pipeline():
    if _pipe["obj"] is None:
        try:
            from hybrid_pipeline import HybridConfig, HybridCrackPipeline
            yolo, unet = os.environ["INFRASCAN_YOLO_CKPT"], os.environ["INFRASCAN_UNET_CKPT"]
            cfg_path = os.environ["INFRASCAN_HYBRID_CONFIG"]
            for p in (yolo, unet, cfg_path):
                if not Path(p).is_file():
                    raise FileNotFoundError(p)
            cfg = HybridConfig.load(cfg_path, os.environ.get("INFRASCAN_HYBRID_KEY", "roi_gated"))
            _pipe["obj"], _pipe["cfg"] = HybridCrackPipeline(yolo, unet, cfg=cfg), cfg
        except Exception as exc:   # missing env var, weights, or dependency
            raise HTTPException(status_code=503, detail=f"Hybrid pipeline unavailable: {exc}")
    return _pipe["obj"], _pipe["cfg"]


@router.post("/images")
async def hybrid_predict(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(415, "Unsupported image type. Upload JPG, PNG, or WEBP.")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "File exceeds the 10 MB limit.")
    bgr = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    if bgr is None:
        raise HTTPException(400, "File could not be decoded as a valid image.")
    if min(bgr.shape[:2]) < 64:
        raise HTTPException(400, "Image too small (minimum dimension: 64 px).")

    pipe, cfg = _get_pipeline()
    scale = min(1.0, MAX_SIDE / max(bgr.shape[:2]))          # same cap as the existing demo
    if scale < 1:
        bgr = cv2.resize(bgr, (int(bgr.shape[1] * scale), int(bgr.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    try:
        res = pipe.predict(bgr, cfg, measure=True)
    except Exception as exc:
        raise HTTPException(500, f"Hybrid inference failed: {exc}")

    image_id = uuid4().hex[:12]
    from hybrid_pipeline import overlay
    vis = overlay(bgr, res["hybrid_mask"], (0, 255, 0))
    for b in res["boxes"]:
        x0, y0, x1, y1 = [int(v) for v in b["xyxy"]]
        cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 255), 2)
    cv2.imwrite(str(OUT_DIR / f"{image_id}_overlay.jpg"), vis)
    cv2.imwrite(str(OUT_DIR / f"{image_id}_mask.png"), res["hybrid_mask"] * 255)
    return {
        "image_id": image_id,
        "status": "completed" if res["yolo_detected"] else "completed_no_yolo_detection",
        "model_version": os.environ.get("INFRASCAN_MODEL_VERSION", "hybrid-v0.1"),
        "processed_dimensions": res["image_size"],
        "pipeline_mode": res["mode"],
        "boxes": res["boxes"],
        "measurements": res["measurements"],            # pixel units only (no calibration supplied)
        "timing_ms": res["timing_ms"],
        "config": res["config"],
        "overlay_url": f"/api/hybrid/images/{image_id}/overlay",
        "mask_url": f"/api/hybrid/images/{image_id}/mask",
        "disclaimer": "Research prototype. Results require qualified engineering review; not a structural safety assessment.",
    }


@router.get("/images/{image_id}/{kind}")
def hybrid_file(image_id: str, kind: str):
    if not image_id.isalnum() or kind not in {"overlay", "mask"}:
        raise HTTPException(400, "Invalid request")
    p = OUT_DIR / f"{image_id}_{kind}.{'jpg' if kind == 'overlay' else 'png'}"
    if not p.is_file():
        raise HTTPException(404, "Not found")
    return FileResponse(p, media_type="image/jpeg" if kind == "overlay" else "image/png")
