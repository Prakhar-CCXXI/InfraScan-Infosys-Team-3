"""FastAPI router for infrastructure damage analysis and AI predictions."""

from datetime import datetime
import io
import logging
from pathlib import Path
import sys
import types
from typing import Any
from uuid import uuid4

import aiofiles
import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
import numpy as np
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import REPO_ROOT, settings
from backend.db.session import get_async_db
from backend.models.prediction import Prediction
from backend.schemas.prediction import InferenceProfile, PredictionResponse
from backend.services.ai_inference import (
    AIInferenceService,
    get_ai_inference_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["Predictions"])
images_router = APIRouter(prefix="/images", tags=["Images"])

PROFILE_DESCRIPTION = (
    "'close_up' = close-up pavement/concrete surface (U-Net crack mask + measurements); "
    "'road_scene' = dashcam-style road image (RDD2022 D00/D10/D20/D40 boxes)."
)


def _ensure_extra_ml_paths() -> None:
    """Ensure preprocessing and explainability folders are importable."""
    for rel in ("data/ml/preprocessing", "data/ml/explain"):
        p = str((REPO_ROOT / rel).resolve())
        if p not in sys.path:
            sys.path.insert(0, p)


def _walk_nn_modules(root: Any):
    """Yield (hint_lower, nn.Module) pairs found inside AIInferenceService / InferenceService."""
    try:
        import torch.nn as nn
    except ImportError:
        return

    visited: set[int] = set()

    def _walk(obj: Any, hint: str = "", depth: int = 0):
        if obj is None or depth > 5 or id(obj) in visited or isinstance(obj, types.ModuleType):
            return
        visited.add(id(obj))

        if isinstance(obj, nn.Module):
            yield f"{hint} {type(obj).__name__}".lower(), obj
            return

        if isinstance(obj, dict):
            for k, v in obj.items():
                yield from _walk(v, f"{hint} {k}", depth + 1)
        elif isinstance(obj, (list, tuple)):
            for idx, v in enumerate(obj):
                yield from _walk(v, f"{hint}[{idx}]", depth + 1)
        else:
            if hasattr(obj, "__dict__"):
                for k, v in vars(obj).items():
                    yield from _walk(v, f"{hint} {k}", depth + 1)
            for slot in getattr(type(obj), "__slots__", ()):
                if isinstance(slot, str) and hasattr(obj, slot):
                    yield from _walk(getattr(obj, slot), f"{hint} {slot}", depth + 1)

    yield from _walk(root)


def _find_loaded_unet(ai_service: Any):
    """Locate the loaded U-Net torch.nn.Module inside AIInferenceService / InferenceService."""
    try:
        import torch
    except ImportError:
        return None, "cpu"

    candidates = []
    for name, mod in _walk_nn_modules(ai_service):
        if "convnext" in name or "_clf" in name or "classif" in name:
            continue
        priority = 0 if ("unet" in name or "seg" in name) else 1
        candidates.append((priority, mod))

    if not candidates:
        return None, torch.device("cpu")

    candidates.sort(key=lambda item: item[0])
    model = candidates[0][1]
    try:
        device = next(model.parameters()).device
    except StopIteration:
        device = torch.device("cpu")
    return model, device


def _find_loaded_classifier(ai_service: Any):
    """Locate the loaded SDNET2018 ConvNeXt-Tiny classifier inside InferenceService."""
    try:
        import torch
    except ImportError:
        return None, "cpu"

    for name, mod in _walk_nn_modules(ai_service):
        if "convnext" in name or "_clf" in name or "classif" in name:
            try:
                device = next(mod.parameters()).device
            except StopIteration:
                device = torch.device("cpu")
            return mod, device
    return None, torch.device("cpu")


def _convnext_gradcam(model: Any, rgb_uint8: np.ndarray, device: Any) -> np.ndarray | None:
    """Compute a leak-free Grad-CAM heatmap on ConvNeXt-Tiny's final feature stage."""
    import torch
    import torch.nn.functional as F
    from image_preprocessing import normalize_imagenet

    features = getattr(model, "features", None)
    if features is None or len(features) == 0:
        return None
    last_stage = features[-1]
    activations: list[torch.Tensor] = []

    def _fwd_hook(_module, _inp, output):
        activations.append(output)

    handle = last_stage.register_forward_hook(_fwd_hook)
    was_training = model.training
    try:
        model.eval()
        rgb256 = cv2.resize(rgb_uint8, (256, 256), interpolation=cv2.INTER_LINEAR)
        x = torch.from_numpy(normalize_imagenet(rgb256)).unsqueeze(0).to(device)
        x.requires_grad_(True)
        with torch.enable_grad():
            logit = model(x).reshape(-1)[0]
            if not activations:
                return None
            acts = activations[0]
            grads = torch.autograd.grad(logit, acts, retain_graph=False)[0]
        weights = grads.mean(dim=(2, 3), keepdim=True)
        cam = F.relu((weights * acts).sum(dim=1, keepdim=True))
        cam_np = cam.squeeze().detach().cpu().numpy().astype(np.float32)
        cmin, cmax = float(cam_np.min()), float(cam_np.max())
        if cmax - cmin > 1e-8:
            return (cam_np - cmin) / (cmax - cmin)
        return np.zeros_like(cam_np)
    finally:
        handle.remove()
        model.zero_grad(set_to_none=True)
        model.train(was_training)


def _extract_bgr_from_preprocess(pre: Any) -> np.ndarray | None:
    """Extract a uint8 BGR image from PreprocessResult regardless of field naming."""
    if pre is None:
        return None

    arr = None
    is_rgb = False

    if isinstance(pre, np.ndarray):
        arr = pre
    else:
        preferred_keys = (
            "bgr",
            "image_bgr",
            "rgb",
            "image_rgb",
            "image",
            "img",
            "processed",
            "resized",
            "array",
        )
        for key in preferred_keys:
            val = getattr(pre, key, None)
            if isinstance(val, np.ndarray) and val.ndim == 3 and val.shape[2] == 3:
                arr = val
                is_rgb = "rgb" in key.lower()
                break

        if arr is None and hasattr(pre, "__dict__"):
            for key, val in vars(pre).items():
                if isinstance(val, np.ndarray) and val.ndim == 3 and val.shape[2] == 3:
                    arr = val
                    is_rgb = "rgb" in key.lower()
                    break

    if arr is None:
        return None
    if arr.dtype != np.uint8:
        max_val = float(arr.max()) if arr.size else 1.0
        scale = 255.0 if max_val <= 1.0 else 1.0
        arr = np.clip(arr * scale, 0, 255).astype(np.uint8)
    if is_rgb:
        arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    return arr

def _save_extra_visuals(
    image_bytes: bytes,
    content_type: str | None,
    profile: str,
    upload_dir: Path,
    stem: str,
    ai_service: AIInferenceService,
    use_classifier_cam: bool = False,
) -> dict[str, str]:
    """Generate and save preprocessed image + Grad-CAM heatmap (U-Net or ConvNeXt fallback) under UPLOAD_DIR."""
    _ensure_extra_ml_paths()
    urls: dict[str, str] = {}

    # 1. Preprocessed image (data/ml/preprocessing/image_preprocessing.py)
    pre_bgr = None
    try:
        from image_preprocessing import preprocess_image

        pre = preprocess_image(image_bytes, content_type)
        pre_bgr = _extract_bgr_from_preprocess(pre)
        if pre_bgr is not None:
            pre_name = f"{stem}_preprocessed.jpg"
            ok, buf = cv2.imencode(".jpg", pre_bgr)
            if ok:
                (upload_dir / pre_name).write_bytes(buf.tobytes())
                urls["pre"] = f"/uploads/{pre_name}"
        else:
            logger.warning(
                "Preprocessed image skipped: no 3-channel array found on %s",
                type(pre).__name__,
            )
    except Exception:
        logger.exception("Preprocessed image export failed")

    # 2. Grad-CAM heatmap for close_up (ConvNeXt-Tiny on hairline fallback, otherwise U-Net)
    if profile == "close_up":
        try:
            import torch
            from gradcam import explain_segmentation, overlay_heatmap

            if pre_bgr is None:
                arr = np.frombuffer(image_bytes, dtype=np.uint8)
                pre_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if pre_bgr is not None:
                rgb = cv2.cvtColor(pre_bgr, cv2.COLOR_BGR2RGB)
                cam = None

                if use_classifier_cam:
                    clf_model, clf_dev = _get_classifier(ai_service)
                    if clf_model is not None:
                        cam = _convnext_gradcam(clf_model, rgb, clf_dev)
                    else:
                        logger.warning("Classifier Grad-CAM skipped: no loaded ConvNeXt module found")
                else:
                    unet_model, device = _find_loaded_unet(ai_service)
                    if unet_model is not None:
                        hook_attrs = (
                            "_forward_hooks",
                            "_forward_pre_hooks",
                            "_backward_hooks",
                            "_backward_pre_hooks",
                        )
                        saved_hooks = {
                            (id(m), attr): set(getattr(m, attr).keys())
                            for m in unet_model.modules()
                            for attr in hook_attrs
                            if hasattr(m, attr)
                        }
                        was_training = unet_model.training
                        try:
                            with torch.enable_grad():
                                cam_out = explain_segmentation(unet_model, rgb, device)
                        finally:
                            for m in unet_model.modules():
                                for attr in hook_attrs:
                                    if hasattr(m, attr):
                                        hooks_dict = getattr(m, attr)
                                        old_keys = saved_hooks.get((id(m), attr), set())
                                        for k in list(hooks_dict.keys()):
                                            if k not in old_keys:
                                                hooks_dict.pop(k, None)
                            unet_model.zero_grad(set_to_none=True)
                            unet_model.train(was_training)

                        if isinstance(cam_out, dict):
                            cam = (
                                cam_out.get("cam")
                                if cam_out.get("cam") is not None
                                else cam_out.get("heatmap")
                            )
                        elif isinstance(cam_out, tuple):
                            arrays = [x for x in cam_out if isinstance(x, np.ndarray)]
                            cam_2d = [x for x in arrays if x.ndim == 2]
                            cam = cam_2d[0] if cam_2d else (arrays[0] if arrays else None)
                        elif isinstance(cam_out, np.ndarray):
                            cam = cam_out
                    else:
                        logger.warning("Grad-CAM skipped: no loaded U-Net nn.Module found on ai_service")

                    # U-Net CAM is flat/near-zero -> fall back to ConvNeXt-Tiny Grad-CAM
                    if _is_flat_cam(cam):
                        clf_model, clf_dev = _get_classifier(ai_service)
                        if clf_model is not None:
                            clf_cam = _convnext_gradcam(clf_model, rgb, clf_dev)
                            if isinstance(clf_cam, np.ndarray) and not _is_flat_cam(clf_cam):
                                cam = clf_cam
                            else:
                                logger.warning("ConvNeXt Grad-CAM fallback also flat; skipping heatmap")
                                cam = None
                        else:
                            logger.warning("U-Net Grad-CAM flat and no ConvNeXt classifier available")
                            cam = None

                if isinstance(cam, np.ndarray):
                    if cam.ndim == 2:
                        if cam.shape[:2] != pre_bgr.shape[:2]:
                            cam = cv2.resize(
                                cam.astype(np.float32),
                                (pre_bgr.shape[1], pre_bgr.shape[0]),
                                interpolation=cv2.INTER_CUBIC,
                            )
                        heat_bgr = overlay_heatmap(pre_bgr, cam, alpha=0.45)
                    else:
                        heat_bgr = cam

                    cam_name = f"{stem}_gradcam.jpg"
                    ok, buf = cv2.imencode(".jpg", heat_bgr)
                    if ok:
                        (upload_dir / cam_name).write_bytes(buf.tobytes())
                        urls["heat"] = f"/uploads/{cam_name}"
        except Exception:
            logger.exception("Grad-CAM export failed")

    return urls

def _serialize_analysis(pred: Prediction) -> dict[str, Any]:
    """Format a persisted Prediction into the Damage Analysis schema expected by Results.jsx."""
    details = pred.defect_details or {}
    raw_inf = details.get("raw_inference") or {}
    meas = details.get("measurements") or {}
    sev = details.get("severity_assessment") or details.get("severity") or {}
    visuals = dict(details.get("visuals") or {})
    detections = details.get("detections") or raw_inf.get("detections") or []
    profile = details.get("profile") or ("road_scene" if detections and not meas else "close_up")

    cls_info = details.get("classification") or raw_inf.get("classification") or {}
    all_warnings = set(details.get("warnings") or []) | set(raw_inf.get("warnings") or [])
    hairline_fallback = "HAIRLINE_CRACK_CLASSIFIER_FALLBACK" in all_warnings

    original_url = visuals.get("original") or f"/uploads/{pred.image_filename}"
    visuals["original"] = original_url

    conf_val = round(
        float(
            (cls_info.get("probability") if hairline_fallback else None)
            or pred.confidence_score
            or 0.0
        ),
        4,
    )

    cracks = []
    if profile == "close_up" and meas:
        crack_type = (
            f"Hairline crack (SDNET2018 ConvNeXt · {conf_val * 100:.1f}%)"
            if hairline_fallback
            else (details.get("defect_type") or "Surface crack (U-Net)")
        )
        cracks.append({
            "id": 1,
            "type": crack_type,
            "confidence": conf_val,
            "lengthPx": round(float(meas.get("length_px") or 0.0), 2),
            "avgWidthPx": round(float(meas.get("mean_width_px") or 0.0), 2),
            "maxWidthPx": round(float(meas.get("max_width_px") or 0.0), 2),
            "areaPx": int(meas.get("area_px") or 0),
            "orientationDeg": round(float(meas.get("orientation_deg") or 0.0), 1),
            "branchPoints": int(meas.get("n_branch_points") or 0),
        })

    raw_density = meas.get("crack_density_percent")
    if raw_density is None:
        raw_density = details.get("crack_density_percentage")

    return {
        "inspectionId": f"PRED-{pred.id}",
        "predictionId": pred.id,
        "assetId": pred.asset_id,
        "profile": profile,
        "sample": False,
        "modelVersion": details.get("model_version") or f"InfraScan ({profile})",
        "images": {
            "original": visuals.get("original"),
            "pre": visuals.get("pre"),
            "detect": visuals.get("detect"),
            "mask": visuals.get("mask"),
            "heat": visuals.get("heat"),
        },
        "cracks": cracks,
        "detections": detections,
        "surfaceDamage": [],
        "crackDensityPct": round(float(raw_density or 0.0), 2),
        "calibrated": bool((meas.get("calibration") or {}).get("mm_per_px")),
        "severity": sev.get("label") or pred.severity_level or "Unknown",
        "severityScore": sev.get("score_0_100"),
        "severityExplanation": sev.get("explanation") or pred.defect_summary,
        "priority": sev.get("suggested_priority") or "Medium Priority",
        "confidence": conf_val,
        "reviewStatus": "Pending engineer review",
    }


def to_http_exception(exc: Exception) -> HTTPException:
    """Map ImageValidationError / ServiceError (anything with .http_status + .to_dict()) to HTTPException."""
    if hasattr(exc, "http_status") and hasattr(exc, "to_dict"):
        return HTTPException(status_code=int(exc.http_status), detail=exc.to_dict())
    logger.exception("Unexpected AI inference failure")
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "status": "error",
            "schema_version": "infrascan-inference-0.1",
            "error": {
                "code": "INFERENCE_FAILED",
                "message": "An error occurred during AI computer vision inference.",
            },
        },
    )


def parse_asset_id(raw_val: Any) -> int:
    """Parse asset identifier into an integer matching the predictions table schema."""
    if raw_val is None:
        return 1
    if isinstance(raw_val, int):
        if raw_val <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Asset ID must be a positive integer.",
            )
        return raw_val

    s = str(raw_val).strip()
    if not s:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'asset_id' cannot be blank.",
        )

    # Check for prefix like 'INF-001'
    if s.upper().startswith("INF-"):
        digits = "".join(c for c in s if c.isdigit())
        if digits:
            val = int(digits)
            if val > 0:
                return val

    try:
        val = int(s)
        if val <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Asset ID must be a positive integer.",
            )
        return val
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid asset identifier '{raw_val}'. Expected positive integer or 'INF-XXX'.",
        ) from exc


async def process_and_store_image(
    file: UploadFile,
    asset_id: int,
    db: AsyncSession,
    ai_service: AIInferenceService,
    profile: str = "close_up",
) -> tuple[Prediction, str]:
    """Validate, run the real AI pipeline, store image + mask/overlay/gradcam on disk, persist to database."""
    # 1. Filename validation
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload payload.",
        )

    # 2. Content-type (MIME) validation
    if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"Unsupported image media type '{file.content_type}'. "
                f"Allowed types are: {', '.join(settings.ALLOWED_IMAGE_TYPES)}"
            ),
        )

    # 3. Read image bytes asynchronously
    try:
        image_bytes = await file.read()
    except Exception as exc:
        logger.error(f"Failed to read uploaded file: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read uploaded image asynchronously.",
        ) from exc

    # 4. Size validation
    file_size = len(image_bytes)
    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image file is empty (0 bytes).",
        )

    if file_size > settings.max_image_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum allowed threshold of {settings.MAX_IMAGE_SIZE_MB}MB.",
        )

    # 5. Deep Format & Integrity Verification (using Pillow)
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            pil_img.verify()
            detected_format = (pil_img.format or "").upper()
            if detected_format not in {"JPEG", "JPG", "PNG", "WEBP"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image structure or unrecognized image format: {detected_format}",
                )
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning(f"Image verification failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is corrupted or not a valid image format.",
        ) from exc

    # 6. Real model inference FIRST (off the event loop, inside the adapter).
    #    Nothing is written to disk or the DB if inference is unavailable (503) or fails.
    file_suffix = Path(file.filename).suffix.lower() or ".jpg"
    stem = f"{uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    unique_filename = f"{stem}{file_suffix}"
    try:
        inference_output = await ai_service.analyze(
            image_bytes=image_bytes,
            filename=unique_filename,
            content_type=file.content_type,
            profile=profile,
            artifact_stem=stem,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise to_http_exception(exc) from exc

    # 7. Store original image + real mask/overlay + preprocessed/gradcam under UPLOAD_DIR
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    destination_path = upload_dir / unique_filename
    visuals: dict[str, str] = {"original": f"/uploads/{unique_filename}"}

    try:
        async with aiofiles.open(destination_path, "wb") as buffer:
            await buffer.write(image_bytes)
        for artifact_name, artifact_bytes in inference_output.artifacts.items():
            async with aiofiles.open(upload_dir / artifact_name, "wb") as buffer:
                await buffer.write(artifact_bytes)
            lower = artifact_name.lower()
            if "mask" in lower:
                visuals["mask"] = f"/uploads/{artifact_name}"
            elif "overlay" in lower or "detect" in lower or "box" in lower:
                visuals["detect"] = f"/uploads/{artifact_name}"
    except Exception as exc:
        logger.error(f"Error persisting file to disk: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist uploaded image file on storage.",
        ) from exc

    # Use ConvNeXt-Tiny Grad-CAM whenever the hairline classifier fallback fired
    details_dict = inference_output.defect_details or {}
    all_warnings = (
        set(details_dict.get("warnings") or [])
        | set((details_dict.get("raw_inference") or {}).get("warnings") or [])
    )
    use_classifier_cam = "HAIRLINE_CRACK_CLASSIFIER_FALLBACK" in all_warnings

    # Generate preprocessed image + Grad-CAM (best-effort; never blocks persistence)
    extra_visuals = _save_extra_visuals(
        image_bytes=image_bytes,
        content_type=file.content_type,
        profile=profile,
        upload_dir=upload_dir,
        stem=stem,
        ai_service=ai_service,
        use_classifier_cam=use_classifier_cam,
    )
    visuals.update(extra_visuals)
    

    enriched_details = dict(details_dict)
    enriched_details["visuals"] = visuals
    enriched_details.setdefault("profile", profile)

    # 8. Persist record (predicted_failure_date stays NULL: no validated model produces it)
    prediction_record = Prediction(
        asset_id=asset_id,
        image_path=str(destination_path),
        image_filename=unique_filename,
        predicted_failure_date=inference_output.predicted_failure_date,
        confidence_score=inference_output.confidence_score,
        recommended_action=inference_output.recommended_action,
        severity_level=inference_output.severity_level,
        defect_summary=inference_output.defect_summary,
        defect_details=enriched_details,
    )

    db.add(prediction_record)
    await db.commit()
    await db.refresh(prediction_record)

    relative_url = f"/uploads/{unique_filename}"
    return prediction_record, relative_url


@router.post(
    "/analyze",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload image and perform AI crack/damage analysis",
    description=(
        "Accepts an infrastructure image, an asset_id and an optional inference `profile`. "
        "Runs the real InferenceService; returns 503 MODEL_UNAVAILABLE if models cannot be loaded "
        "(mock output only when ALLOW_MOCK_INFERENCE=1, and then tagged defect_details.source='mock')."
    ),
    responses={503: {"description": "Models unavailable (MODEL_UNAVAILABLE)"}},
)
async def analyze_infrastructure_image(
    asset_id: Any = Form(..., description="Unique infrastructure asset identifier (e.g. 1 or INF-001)"),
    file: UploadFile = File(..., description="Uploaded infrastructure inspection image"),
    profile: InferenceProfile = Form("close_up", description=PROFILE_DESCRIPTION),
    db: AsyncSession = Depends(get_async_db),
    ai_service: AIInferenceService = Depends(get_ai_inference_service),
) -> Prediction:
    """Validate image, run AI analysis, persist prediction, and return it."""
    parsed_id = parse_asset_id(asset_id)
    prediction_record, _ = await process_and_store_image(
        file=file,
        asset_id=parsed_id,
        db=db,
        ai_service=ai_service,
        profile=profile,
    )
    return prediction_record


@images_router.post(
    "/upload",
    status_code=status.HTTP_201_CREATED,
    summary="Upload inspection images from frontend form, store on backend, and run AI analysis",
)
async def upload_frontend_images(
    images: list[UploadFile] = File(None, description="Multiple uploaded images"),
    file: UploadFile = File(None, description="Single uploaded image"),
    assetId: str | None = Form(None),
    asset_id: str | None = Form(None),
    date: str | None = Form(None),
    inspector: str | None = Form(None),
    notes: str | None = Form(None),
    profile: InferenceProfile = Form("close_up", description=PROFILE_DESCRIPTION),
    db: AsyncSession = Depends(get_async_db),
    ai_service: AIInferenceService = Depends(get_ai_inference_service),
) -> dict[str, Any]:
    """Endpoint consumed by frontend Upload form. Receives image(s), saves to backend, and returns AI findings."""
    raw_asset = assetId or asset_id or "1"
    parsed_asset_id = parse_asset_id(raw_asset)

    # Consolidate uploaded files
    file_list: list[UploadFile] = []
    if images:
        file_list.extend(images)
    if file and file not in file_list:
        file_list.append(file)

    if not file_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one valid image to upload.",
        )

    saved_images = []
    predictions_data = []

    for item in file_list:
        record, image_url = await process_and_store_image(
            file=item,
            asset_id=parsed_asset_id,
            db=db,
            ai_service=ai_service,
            profile=profile,
        )

        saved_images.append({
            "filename": record.image_filename,
            "image_path": record.image_path,
            "image_url": image_url,
        })

        predictions_data.append({
            "id": record.id,
            "asset_id": record.asset_id,
            "severity_level": record.severity_level,
            "confidence_score": record.confidence_score,
            "recommended_action": record.recommended_action,
            "predicted_failure_date": record.predicted_failure_date.isoformat() if record.predicted_failure_date else None,
            "defect_summary": record.defect_summary,
            "defect_details": record.defect_details,
            "image_url": image_url,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })

    primary_prediction = predictions_data[0]
    details = primary_prediction["defect_details"] or {}
    show_conf = details.get("confidence_basis") == "max_detection_confidence"
    conf_txt = f" (Confidence: {int(primary_prediction['confidence_score'] * 100)}%)" if show_conf else ""
    mock_txt = " [MOCK DATA - models unavailable]" if details.get("source") == "mock" else ""
    return {
        "status": "success",
        "message": (
            f"Successfully stored {len(file_list)} image(s) in backend storage!{mock_txt} "
            f"AI Assessment: {primary_prediction['severity_level']}{conf_txt}. "
            f"Action: {primary_prediction['recommended_action'][:80]}..."
        ),
        "count": len(file_list),
        "asset_id": parsed_asset_id,
        "inspector": inspector,
        "date": date,
        "profile": profile,
        "stored_images": saved_images,
        "predictions": predictions_data,
    }


@router.get(
    "/latest/analysis",
    summary="Retrieve the latest persisted AI damage analysis for the frontend Results page",
)
async def get_latest_analysis(db: AsyncSession = Depends(get_async_db)) -> dict[str, Any]:
    result = await db.execute(select(Prediction).order_by(Prediction.id.desc()).limit(1))
    pred = result.scalar_one_or_none()
    if pred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No predictions available yet.",
        )
    return _serialize_analysis(pred)


@router.get(
    "/{prediction_id}/analysis",
    summary="Retrieve full AI damage analysis (images, geometry, severity) for a prediction",
)
async def get_prediction_analysis(
    prediction_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> dict[str, Any]:
    result = await db.execute(select(Prediction).where(Prediction.id == prediction_id))
    pred = result.scalar_one_or_none()
    if pred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction with ID {prediction_id} not found.",
        )
    return _serialize_analysis(pred)


@router.get(
    "/{prediction_id}",
    response_model=PredictionResponse,
    summary="Retrieve prediction by record ID",
)
async def get_prediction_by_id(
    prediction_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> Prediction:
    """Retrieve an existing AI damage prediction by its primary key ID."""
    query = select(Prediction).where(Prediction.id == prediction_id)
    result = await db.execute(query)
    prediction = result.scalar_one_or_none()

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction with ID {prediction_id} not found.",
        )
    return prediction


@router.get(
    "/asset/{asset_id}",
    response_model=list[PredictionResponse],
    summary="Retrieve all predictions for a specific infrastructure asset",
)
async def get_predictions_for_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_async_db),
) -> list[Prediction]:
    """Retrieve all historic AI predictions linked to a given asset_id."""
    query = (
        select(Prediction)
        .where(Prediction.asset_id == asset_id)
        .order_by(Prediction.created_at.desc())
    )
    result = await db.execute(query)
    predictions = result.scalars().all()
    return list(predictions)