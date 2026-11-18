"""Tests for inference_output.py against docs/api_contract/inference_result.schema.json (no torch needed).  Run: python ml/hybrid/test_inference_output.py"""
import copy, json, sys
from pathlib import Path
import cv2, jsonschema, numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import inference_output as IO
from geometry import crack_geometry

SCHEMA = jsonschema.Draft7Validator(json.loads((HERE.parents[1] / "docs/api_contract/inference_result.schema.json").read_text()))
REG = {m["id"]: m for m in json.loads((HERE.parent / "registry/model_registry.json").read_text())["models"]}
UNET = dict(role="segmentation", id="crack500-unet-resnet34-v1.0", sha256=REG["crack500-unet-resnet34-v1.0"]["checkpoint"]["sha256"])
YOLO = dict(role="localisation", id="crack500-yolo11n-seg-v0.1", sha256=REG["crack500-yolo11n-seg-v0.1"]["checkpoint"]["sha256"])
H, W = 360, 640
M = np.zeros((H, W), np.uint8); cv2.polylines(M, [np.array([(60, 300), (200, 200), (330, 210), (520, 60)])], False, 1, 4)


def res(mask=M, det=True, mode="full_image_dual_threshold"):
    return dict(mode=mode, image_size=dict(width=mask.shape[1], height=mask.shape[0]), yolo_detected=det,
                boxes=[dict(xyxy=[55.2, 55.0, 525.9, 305.1], conf=0.81)] if det else [], yolo_mask=mask, hybrid_mask=mask, hybrid_prob=None,
                timing_ms=dict(yolo_ms=18.4, unet_fuse_ms=38.1, total_ms=56.5), config=dict(yolo_conf=0.1, gate="mask", margin=8, t_in=0.4, t_out=0.9),
                measurements=crack_geometry(mask))


def valid(d): return not list(SCHEMA.iter_errors(d))


def test_registry_hashes_are_64_hex():
    assert len(UNET["sha256"]) == 64 and len(YOLO["sha256"]) == 64


def test_valid_documents():
    assert valid(IO.build_inference_result(res(), pipeline_name="hybrid_dual_threshold", unet_thr=0.4, models=[UNET, YOLO], resize_scale=0.43, quality_flag_codes=["POSSIBLE_BLUR"]))
    assert valid(IO.build_inference_result(res(), pipeline_name="hybrid_dual_threshold", unet_thr=0.4, models=[UNET, YOLO], mm_per_px=0.5, calibration_source="ruler in frame"))
    d0 = IO.build_inference_result(res(np.zeros((H, W), np.uint8), det=False, mode="no_detection_empty"), pipeline_name="hybrid_roi_gated", unet_thr=0.4, models=[UNET, YOLO])
    assert valid(d0) and {"NO_YOLO_DETECTION", "EMPTY_MASK"} <= set(d0["warnings"]) and d0["measurement_uncertainty"]["width_reliability"] == "unknown"
    assert valid(IO.error_result("MODEL_UNAVAILABLE", "weights not found"))


def test_invalid_documents_rejected():
    ok = IO.build_inference_result(res(), pipeline_name="hybrid_dual_threshold", unet_thr=0.4, models=[UNET, YOLO])
    for mut in (lambda d: d["measurements"]["calibration"].update(mm_per_px=0.5), lambda d: d["detections"][0].update(confidence=1.7),
                lambda d: d.pop("measurement_uncertainty"), lambda d: d.update(extra=1), lambda d: d["models"][1].update(sha256=d["models"][1]["sha256"] + "b")):
        bad = copy.deepcopy(ok); mut(bad); assert not valid(bad)


def test_thin_crack_flag_is_resolution_aware():
    thin = np.zeros((H, W), np.uint8); cv2.line(thin, (50, 300), (550, 60), 1, 6)        # drawn width about 8 px -> thin at 640 px scale
    thick = np.zeros((H, W), np.uint8); cv2.line(thick, (50, 300), (550, 60), 1, 40)     # about 42 px -> not thin
    f = lambda m: IO.build_inference_result(res(m), pipeline_name="hybrid_dual_threshold", unet_thr=0.4, models=[UNET, YOLO])["measurement_uncertainty"]["width_reliability"]
    assert f(thin) == "low_thin_crack" and f(thick) == "normal"
    big = cv2.resize(thin, (1280, 720), interpolation=cv2.INTER_NEAREST)                  # same crack at 2x resolution -> still thin
    assert IO.build_inference_result(res(big), pipeline_name="hybrid_dual_threshold", unet_thr=0.4, models=[UNET, YOLO])["measurement_uncertainty"]["width_reliability"] == "low_thin_crack"


def test_png_roundtrip():
    back = cv2.imdecode(np.frombuffer(IO.encode_mask_png(M), np.uint8), cv2.IMREAD_GRAYSCALE)
    assert ((back > 0) == (M > 0)).all() and set(np.unique(back)) == {0, 255}


if __name__ == "__main__":
    for n in [n for n in dir() if n.startswith("test_")]: globals()[n](); print("PASS", n)
