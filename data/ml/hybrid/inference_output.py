"""
Turns pipeline outputs into the documented JSON structure (docs/api_contract/inference_result.schema.json).
This is the AI/ML side of the contract: the backend only stores files, adds ids and fills the 'uri' fields.

  res = pipe.predict(bgr, cfg)                                   # hybrid pipelines
  res = predict_unet_only(pipe, bgr, thr=0.4)                    # U-Net only (no YOLO weights needed)
  out = build_inference_result(res, pipeline_name="hybrid_dual_threshold", unet_thr=0.4, models=[...], resize_scale=meta["resize_scale"],
                               quality_flag_codes=meta["quality_checks"]["flag_codes"])
  png_bytes = encode_mask_png(res["hybrid_mask"])                # backend stores this and sets out["mask"]["uri"]
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry import crack_geometry  # noqa: E402

SCHEMA_VERSION = "infrascan-inference-0.1"
DISCLAIMER = "Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment."

# Source: geometry validation on the 348 Crack500 validation images (U-Net masks at 0.4 vs annotated masks, pixel units).
GEOMETRY_UNCERTAINTY_V1 = dict(
    basis="Crack500 validation split, U-Net masks (threshold 0.4) vs annotated masks, pixel units; relative error = (predicted - reference) / reference",
    reference="annotated_masks_not_physical_truth", n_validation_images=348,
    relative_error=dict(length=dict(median_signed=-0.1072, iqr=[-0.2411, 0.0049]), mean_width=dict(median_signed=0.1681, iqr=[0.0079, 0.3611]),
                        max_width=dict(median_signed=0.0684, iqr=[-0.0717, 0.2333]), area=dict(median_signed=0.0623, iqr=[-0.0762, 0.2144])),
    orientation_error_deg=dict(median=1.07, within_10deg_fraction=0.886),
    width_reliability="unknown",
    notes=["Length tends to be underestimated and mean width overestimated, even for good segmentations.",
           "Thin-crack widths are unreliable (median +36%); area and orientation are the most robust measures.",
           "Segmentation failures (about 6% of validation images) make all geometry meaningless.",
           "width_reliability = low_thin_crack when the mean width, normalised to a 640 px longest side, is below 15.23 px (lower tercile on Crack500 validation); the normalisation by image size is an assumption."])
# Thin-crack flag. Ground-truth lower tercile = 12.75 px on 640x360 images, but the flag is applied to PREDICTED widths (biased ~+17%),
# so the threshold must come from the lower tercile of pr_mean_width in geometry_per_image_val.csv. None -> width_reliability stays "unknown".
THIN_WIDTH_PX_AT_640 = 15.23   # lower tercile of PREDICTED mean width on Crack500 validation (0.33 quantile = 15.230715; 0.67 = 24.653539)
REFERENCE_LONG_SIDE = 640.0       # widths are normalised to a 640-px longest side before comparing with the threshold


def encode_mask_png(mask) -> bytes:
    ok, buf = cv2.imencode(".png", (np.asarray(mask) > 0).astype(np.uint8) * 255)
    assert ok
    return buf.tobytes()


def predict_unet_only(pipe, bgr, thr=0.4, measure=True):
    """Same result structure as HybridCrackPipeline.predict, for the U-Net alone (pipe may be created with yolo_ckpt=None)."""
    H, W = bgr.shape[:2]
    pipe.sync(); t0 = time.perf_counter()
    prob = pipe.unet_prob(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)); mask = (prob >= thr).astype(np.uint8)
    pipe.sync(); ms = 1000 * (time.perf_counter() - t0)
    res = dict(mode="unet_full_image", image_size=dict(width=W, height=H), yolo_detected=False, boxes=[], yolo_mask=np.zeros((H, W), np.uint8),
               hybrid_mask=mask, hybrid_prob=prob, timing_ms=dict(yolo_ms=None, unet_fuse_ms=ms, total_ms=ms), config=dict(unet_threshold=thr))
    if measure:
        res["measurements"] = crack_geometry(mask)
    return res


def build_inference_result(res, *, pipeline_name, unet_thr, models, resize_scale=1.0, quality_flag_codes=(), mm_per_px=None, calibration_source=None,
                           mask_uri=None, overlay_uri=None):
    if mm_per_px is not None and not calibration_source:
        raise ValueError("calibration_source is required when mm_per_px is given")
    W, H = res["image_size"]["width"], res["image_size"]["height"]
    mask = res["hybrid_mask"]; pos = int((mask > 0).sum())
    g = res.get("measurements") or crack_geometry(mask)
    m = dict(unit="mm" if mm_per_px else "px", reference_frame="processed_image", calibration=dict(mm_per_px=mm_per_px, source=calibration_source if mm_per_px else None),
             length_px=round(float(g["length_px"]), 2), mean_width_px=round(float(g["mean_width_px"]), 2), max_width_px=round(float(g["max_width_px"]), 2),
             area_px=int(g["area_px"]), crack_density_percent=round(float(g["crack_density_percent"]), 4),
             orientation_deg=None if g["orientation_deg"] is None else round(float(g["orientation_deg"]), 2),
             n_components=int(g["n_components"]), n_branch_points=int(g["n_branch_points"]), n_endpoints=int(g["n_endpoints"]))
    if mm_per_px:
        m.update(length_mm=round(m["length_px"] * mm_per_px, 3), mean_width_mm=round(m["mean_width_px"] * mm_per_px, 3),
                 max_width_mm=round(m["max_width_px"] * mm_per_px, 3), area_mm2=round(m["area_px"] * mm_per_px ** 2, 3))
    unc = dict(GEOMETRY_UNCERTAINTY_V1)
    if THIN_WIDTH_PX_AT_640 is not None and pos > 0:
        w640 = m["mean_width_px"] * REFERENCE_LONG_SIDE / float(max(W, H))
        unc["width_reliability"] = "low_thin_crack" if w640 < THIN_WIDTH_PX_AT_640 else "normal"
    warns = []
    if not res["yolo_detected"] and pipeline_name != "unet_only": warns.append("NO_YOLO_DETECTION")
    if pos == 0: warns.append("EMPTY_MASK")
    warns += [c for c in quality_flag_codes if c in ("LOW_LIGHT", "POSSIBLE_BLUR")]
    if not mm_per_px: warns.append("PIXEL_UNITS_ONLY")
    cfg = {k: v for k, v in res.get("config", {}).items() if k in ("yolo_conf", "gate", "margin", "t_in", "t_out")}
    cfg["unet_threshold"] = unet_thr
    t = res["timing_ms"]
    out = dict(status="ok", schema_version=SCHEMA_VERSION, pipeline=dict(name=pipeline_name, mode=res["mode"], config=cfg), models=list(models),
               coordinate_frame=dict(width=W, height=H, origin="top-left, x right, y down", resize_scale_to_original=round(float(resize_scale), 6)),
               detections=[dict(id=i, box_xyxy=[round(float(v), 1) for v in b["xyxy"]], confidence=round(float(b["conf"]), 4), source="yolo") for i, b in enumerate(res["boxes"])],
               mask=dict(encoding="png_0_255", uri=mask_uri, width=W, height=H, positive_pixels=pos, area_fraction=round(pos / float(W * H), 6)),
               measurements=m, measurement_uncertainty=unc, warnings=sorted(set(warns), key=warns.index),
               timing_ms=dict(yolo_ms=None if t.get("yolo_ms") is None else round(float(t["yolo_ms"]), 2), unet_fuse_ms=round(float(t["unet_fuse_ms"]), 2), total_ms=round(float(t["total_ms"]), 2)),
               disclaimer=DISCLAIMER)
    if overlay_uri is not None:
        out["overlay"] = dict(uri=overlay_uri)
    return out


def error_result(code, message):
    return dict(status="error", schema_version=SCHEMA_VERSION, error=dict(code=code, message=message))
