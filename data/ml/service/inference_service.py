"""
Unified inference service for the FastAPI backend (framework-agnostic: no FastAPI import).

  svc = InferenceService(ServiceConfig.from_env())          # env vars below; models load lazily on first use
  out = svc.analyze(raw_bytes, "image/jpeg", profile="close_up")      # or profile="road_scene"
  out.result      -> JSON-safe dict (close_up: inference_result.schema.json, road_scene: road_scene_result.schema.json)
  out.preprocessing -> preprocessing_result.schema.json (merge it into the API response)
  out.mask_png / out.overlay_jpg -> bytes for the backend to store (then fill result["mask"]["uri"] / result["overlay"]["uri"])
Errors: pp.ImageValidationError (bad upload: .code .message .http_status .to_dict()) or ServiceError (.code .message .http_status .to_dict()).

PROFILES are chosen by the CALLER (no automatic scene detection):
  close_up   : close-up pavement/concrete surface -> U-Net mask (+ YOLO boxes via the dual-threshold hybrid if a crack-YOLO checkpoint is set)
               -> pixel geometry -> severity.  Falls back to SDNET2018 ConvNeXt-Tiny concrete classifier when U-Net returns an empty mask.
  road_scene : dashcam-style road image -> RDD2022 detector (D00/D10/D20/D40 boxes) -> severity from detections.
The SDNET classifier is not meaningful on road scenes (Grad-CAM smoke test: heat on sky and trees), so it is never run for road_scene.

Env vars: INFRASCAN_UNET_CKPT, INFRASCAN_YOLO_CKPT (optional), INFRASCAN_RDD_CKPT, INFRASCAN_CLS_CKPT (optional), INFRASCAN_HYBRID_CONFIG,
          INFRASCAN_SEVERITY_CONFIG, INFRASCAN_REGISTRY, INFRASCAN_DEVICE, INFRASCAN_VERIFY_HASHES (default 1)
Requires on sys.path: image_preprocessing, hybrid_pipeline, geometry, inference_output, severity_engine (sibling folders are added automatically).
Usage with FastAPI (the backend's job): one global service; call svc.analyze(...) in a thread pool; map ImageValidationError/ServiceError .http_status.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_HERE = Path(__file__).resolve().parent
for _sub in ("preprocessing", "hybrid", "severity"):
    _p = _HERE.parent / _sub
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import image_preprocessing as pp  # noqa: E402
import severity_engine as sev  # noqa: E402
from hybrid_pipeline import HybridConfig, HybridCrackPipeline, overlay  # noqa: E402
from inference_output import DISCLAIMER, build_inference_result, encode_mask_png, error_result, predict_unet_only  # noqa: E402

IDS = dict(unet="crack500-unet-resnet34-v1.0", yolo="crack500-yolo11n-seg-v0.1", cls="sdnet2018-convnext-tiny-v1.0", rdd="rdd2022-yolo11s-v1.0")
ROLES = dict(unet="segmentation", yolo="localisation", cls="classification", rdd="detection")
RDD_CLASSES = ["D00", "D10", "D20", "D40"]
ROAD_SCHEMA_VERSION = "infrascan-roadscene-0.1"
# Peak of the all-class F1 curve (F1 = 0.38) read from the detector's BoxF1_curve.png (team report: validation split; per class: D20 ~0.33, D40 and D00 ~0.21, D10 unreliable).
RDD_CONF_VALIDATED = 0.233
PROFILES = ("close_up", "road_scene")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ServiceError(Exception):
    """code: MODEL_UNAVAILABLE | INFERENCE_FAILED | INVALID_INPUT"""
    def __init__(self, code, message, http_status=500):
        super().__init__(message); self.code, self.message, self.http_status = code, message, http_status

    def to_dict(self):
        return error_result(self.code, self.message)


@dataclass
class ServiceConfig:
    unet_ckpt: str | None = None
    yolo_ckpt: str | None = None
    rdd_ckpt: str | None = None
    cls_ckpt: str | None = None
    hybrid_config: str | None = None
    severity_config: str | None = None
    registry: str | None = None
    device: str | None = None
    verify_hashes: bool = True
    unet_thr: float = 0.4
    rdd_conf: float = RDD_CONF_VALIDATED   # any other value is reported with the UNVALIDATED_OPERATING_POINT warning
    cls_thr: float = 0.5058         # ConvNeXt fold-0 validation recall-90% threshold (registry)
    cls_size: int = 256

    @staticmethod
    def from_env():
        g = os.environ.get
        return ServiceConfig(unet_ckpt=g("INFRASCAN_UNET_CKPT"), yolo_ckpt=g("INFRASCAN_YOLO_CKPT"), rdd_ckpt=g("INFRASCAN_RDD_CKPT"), cls_ckpt=g("INFRASCAN_CLS_CKPT"),
                             hybrid_config=g("INFRASCAN_HYBRID_CONFIG"), severity_config=g("INFRASCAN_SEVERITY_CONFIG"), registry=g("INFRASCAN_REGISTRY"),
                             device=g("INFRASCAN_DEVICE"), verify_hashes=g("INFRASCAN_VERIFY_HASHES", "1") not in ("0", "false", "False"))


@dataclass
class AnalysisOutput:
    profile: str
    result: dict
    preprocessing: dict
    mask_png: bytes | None = None
    overlay_jpg: bytes | None = None


def _sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()

def _filter_stain_blobs(mask, min_area=600, solidity_thr=0.72, aspect_thr=1.7):
    """Zero out compact, non-elongated components (stains). Returns (mask, n_removed)."""
    n, labels, stats, _ = cv2.connectedComponentsWithStats((mask > 0).astype(np.uint8), connectivity=8)
    drop = []
    for i in range(1, n):
        x, y, w, h, area = [int(v) for v in stats[i]]
        if area < min_area:
            continue
        comp = (labels[y:y + h, x:x + w] == i).astype(np.uint8)
        cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not cnts:
            continue
        pts = np.vstack(cnts)
        hull_area = cv2.contourArea(cv2.convexHull(pts))
        if hull_area <= 0:
            continue
        (_, _), (rw, rh), _ = cv2.minAreaRect(pts)
        aspect = max(rw, rh) / max(min(rw, rh), 1e-6)
        if area / hull_area > solidity_thr and aspect < aspect_thr:
            drop.append(i)
    if not drop:
        return mask, 0
    out = mask.copy()
    out[np.isin(labels, drop)] = 0
    return out, len(drop)


def _remeasure_mask(mask, old: dict) -> dict:
    """Recompute the pixel measurements the API reads (only keys already present in `old`) from the filtered mask."""
    from skimage.morphology import skeletonize
    binary = (mask > 0).astype(np.uint8)
    H, W = binary.shape[:2]
    area = int(binary.sum())
    vals = dict(area_px=area, crack_density_percent=round(100.0 * area / float(H * W), 4),
                length_px=0.0, mean_width_px=0.0, max_width_px=0.0, orientation_deg=0.0, n_branch_points=0)
    if area:
        sk = skeletonize(binary > 0).astype(np.uint8)
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
        if sk.any():
            vals["length_px"] = float(sk.sum())
            vals["mean_width_px"] = float(max(1.0, 2.0 * dist[sk > 0].mean() - 1.0))
            vals["max_width_px"] = float(max(1.0, 2.0 * dist[sk > 0].max() - 1.0))
            nb = cv2.filter2D(sk, -1, np.ones((3, 3), np.float32), borderType=cv2.BORDER_CONSTANT) - sk
            vals["n_branch_points"] = int(cv2.connectedComponents(((sk == 1) & (nb >= 3)).astype(np.uint8), connectivity=8)[0] - 1)
            ys, xs = np.nonzero(sk)
            if len(xs) >= 2:
                vx, vy = cv2.fitLine(np.column_stack([xs, ys]).astype(np.float32), cv2.DIST_L2, 0, 0.01, 0.01).ravel()[:2]
                vals["orientation_deg"] = float(np.degrees(np.arctan2(vy, vx)) % 180.0)
    new = dict(old)
    new.update({k: v for k, v in vals.items() if k in old})
    return new
class InferenceService:
    def __init__(self, cfg: ServiceConfig):
        self.cfg, self._lock = cfg, threading.Lock()
        self._pipe = self._rdd = self._clf = self._hybrid_cfg = None
        self.loaded: dict[str, str] = {}      # model id -> sha256 ("" if unverified)
        reg = Path(cfg.registry) if cfg.registry else None
        self._registry = {m["id"]: m for m in json.loads(reg.read_text())["models"]} if reg and reg.is_file() else {}
        self._sev_cfg = sev.load_config(cfg.severity_config or Path(sev.__file__).with_name("severity_config.json"))

    # ---------------- loading ----------------
    def _verify(self, key, path):
        if not path or not Path(path).is_file():
            raise ServiceError("MODEL_UNAVAILABLE", f"{IDS[key]}: checkpoint not found ({path})", 503)
        sha = _sha256(path); want = (self._registry.get(IDS[key]) or {}).get("checkpoint", {}).get("sha256")
        if self.cfg.verify_hashes and isinstance(want, str) and _HEX64.match(want) and want != sha:
            raise ServiceError("MODEL_UNAVAILABLE", f"{IDS[key]}: checksum mismatch (file {sha[:12]}..., registry {want[:12]}...)", 503)
        self.loaded[IDS[key]] = sha if (isinstance(want, str) and want == sha) else ""
        return sha

    def _ref(self, key):
        sha = self.loaded.get(IDS[key]) or None
        return dict(role=ROLES[key], id=IDS[key], sha256=sha if sha and _HEX64.match(sha) else None)

    def _ensure_closeup(self):
        if self._pipe is None:
            self._verify("unet", self.cfg.unet_ckpt)
            use_yolo = bool(self.cfg.yolo_ckpt)
            if use_yolo:
                self._verify("yolo", self.cfg.yolo_ckpt)
                if not self.cfg.hybrid_config or not Path(self.cfg.hybrid_config).is_file():
                    raise ServiceError("MODEL_UNAVAILABLE", "hybrid_config.json is required when a crack YOLO checkpoint is set", 503)
                self._hybrid_cfg = HybridConfig.load(self.cfg.hybrid_config, "dual_threshold")
                self.cfg.unet_thr = float(json.loads(Path(self.cfg.hybrid_config).read_text()).get("unet_thr", self.cfg.unet_thr))
            self._pipe = HybridCrackPipeline(self.cfg.yolo_ckpt if use_yolo else None, self.cfg.unet_ckpt, device=self.cfg.device, cfg=self._hybrid_cfg)
        return self._pipe

    def _ensure_rdd(self):
        if self._rdd is None:
            self._verify("rdd", self.cfg.rdd_ckpt)
            from ultralytics import YOLO
            m = YOLO(self.cfg.rdd_ckpt); names = [m.names[i] for i in range(len(m.names))]
            if names != RDD_CLASSES:
                raise ServiceError("MODEL_UNAVAILABLE", f"unexpected detector classes {names}", 503)
            self._rdd = m
        return self._rdd

    def _ensure_clf(self):
        if self._clf is None:
            ckpt = self.cfg.cls_ckpt
            if not ckpt:
                default_ckpt = _HERE.parent.parent / "sdnet2018_classification" / "checkpoints" / "ConvNeXt-Tiny" / "best.pt"
                if default_ckpt.is_file():
                    ckpt = str(default_ckpt)
            self._verify("cls", ckpt)
            import torch
            from torchvision import models
            dev = torch.device(self.cfg.device or ("cuda" if torch.cuda.is_available() else "cpu"))
            m = models.convnext_tiny(weights=None); m.classifier[-1] = torch.nn.Linear(m.classifier[-1].in_features, 1)   # same head as train_classifier.py
            state = torch.load(ckpt, map_location=dev)
            m.load_state_dict(state["model"] if isinstance(state, dict) and "model" in state else state)
            self._clf = m.to(dev).eval()
        return self._clf

    def health(self):
        return dict(loaded_models=dict(self.loaded), severity_config=dict(id=self._sev_cfg["config_id"], status=self._sev_cfg["status"]), device=self.cfg.device or "auto")

    # ---------------- public API ----------------
    def analyze(self, raw: bytes, content_type: str | None = None, profile: str = "close_up", *, mm_per_px=None, calibration_source=None,
                classify: bool = False, return_overlay: bool = True) -> AnalysisOutput:
        if profile not in PROFILES:
            raise ServiceError("INVALID_INPUT", f"profile must be one of {PROFILES}", 400)
        if mm_per_px is not None and not calibration_source:
            raise ServiceError("INVALID_INPUT", "calibration_source is required when mm_per_px is given", 400)
        pre = pp.preprocess_image(raw, content_type)       # raises ImageValidationError
        meta = pre.to_dict()
        try:
            with self._lock:                               # one inference at a time per process (GPU memory, model state)
                if profile == "close_up":
                    return self._closeup(pre.processed_bgr, meta, mm_per_px, calibration_source, classify, return_overlay)
                return self._road(pre.processed_bgr, meta, return_overlay)
        except (ServiceError, pp.ImageValidationError):
            raise
        except Exception as e:
            raise ServiceError("INFERENCE_FAILED", f"{type(e).__name__}: {e}", 500)

    # ---------------- close-up ----------------
    def _closeup(self, bgr, meta, mm_per_px, calibration_source, classify, return_overlay):
        pipe = self._ensure_closeup(); thr = self.cfg.unet_thr
        hybrid = self._hybrid_cfg is not None and getattr(pipe, "yolo", None) is not None
        if hybrid:
            res, name, keys = pipe.predict(bgr, self._hybrid_cfg, measure=True), "hybrid_dual_threshold", ("unet", "yolo")
        else:
            res, name, keys = predict_unet_only(pipe, bgr, thr, measure=True), "unet_only", ("unet",)

        n_blobs = 0
        try:
            filtered, n_blobs = _filter_stain_blobs(res["hybrid_mask"])
            if n_blobs:
                res = dict(res, hybrid_mask=filtered)
        except Exception as exc:
            logger.warning("Stain-blob filter skipped: %s", exc)

        out = build_inference_result(
            res,
            pipeline_name=name,
            unet_thr=thr,
            models=[self._ref(k) for k in keys],
            resize_scale=meta["resize_scale"],
            quality_flag_codes=meta["quality_checks"]["flag_codes"],
            mm_per_px=mm_per_px,
            calibration_source=calibration_source,
        )

        if n_blobs:
            out["warnings"].append("STAIN_BLOB_FILTERED")
            try:
                if isinstance(out.get("measurements"), dict):
                    out["measurements"] = _remeasure_mask(res["hybrid_mask"], out["measurements"])
                if isinstance(out.get("mask"), dict) and "positive_pixels" in out["mask"]:
                    out["mask"]["positive_pixels"] = int((res["hybrid_mask"] > 0).sum())
            except Exception as exc:
                logger.warning("Re-measure after stain filter failed: %s", exc)

        size = out["coordinate_frame"]
        out["severity"] = sev.assess(out["measurements"], None, dict(width=size["width"], height=size["height"]), out["warnings"], self._sev_cfg, mm_per_px)

        empty_mask = out["mask"]["positive_pixels"] == 0
        density = float((out.get("measurements") or {}).get("crack_density_percent") or 0.0)
        low_density = density < 0.25
        if classify or empty_mask or low_density:
            try:
                cls_res = self._classify(bgr)
                out["classification"] = cls_res
                out["models"].append(self._ref("cls"))
                if empty_mask and cls_res["decision"]:
                    prob = cls_res["probability"]
                    out["warnings"].append("HAIRLINE_CRACK_CLASSIFIER_FALLBACK")
                    out["severity"] = dict(
                        out["severity"],
                        category="LOW",
                        label="Hairline Crack Detected (Classifier)",
                        score_0_100=round(prob * 40.0, 1),
                        suggested_priority="Low Priority",
                        engineering_review_required=True,
                        confidence="MEDIUM",
                        explanation=(
                            f"U-Net segmentation produced an empty mask on this low-contrast concrete surface, "
                            f"but the SDNET2018 ConvNeXt-Tiny classifier detected a hairline crack "
                            f"(confidence {prob * 100:.1f}%, threshold {cls_res['threshold'] * 100:.1f}%). "
                            f"Pixel geometry is unavailable; inspect the Grad-CAM heatmap."
                        ),
                    )
                elif not empty_mask and low_density and cls_res["decision"]:
                    prob = cls_res["probability"]
                    out["warnings"].append("HAIRLINE_CRACK_CLASSIFIER_FALLBACK")
                    sv = out["severity"]
                    sv["engineering_review_required"] = True
                    sv["explanation"] = (
                        f"{sv.get('explanation') or ''} Partial mask (density {density:.2f}%) but the SDNET2018 "
                        f"ConvNeXt-Tiny classifier flags a crack (probability {prob * 100:.1f}%, "
                        f"threshold {cls_res['threshold'] * 100:.1f}%); mask may under-segment. Engineer review required."
                    ).strip()
            except ServiceError as exc:
                if classify:
                    raise
                logger.warning("SDNET2018 fallback classifier skipped: %s", exc)

        ov = None
        if return_overlay:
            vis = overlay(bgr, res["hybrid_mask"], (0, 255, 0))
            for b in res["boxes"]:
                x0, y0, x1, y1 = [int(v) for v in b["xyxy"]]; cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 255), 2)
            ov = cv2.imencode(".jpg", vis)[1].tobytes()
        return AnalysisOutput("close_up", out, meta, encode_mask_png(res["hybrid_mask"]), ov)
    def _classify(self, bgr):
        """IMAGE-LEVEL classification from 256x256 tiles: probability = MAX tile probability, decision = max >= threshold. UNVALIDATED aggregation:
        at the recall-90% operating point a patch false-alarm rate of ~13% makes 'any tile' very likely to fire on images with many tiles."""
        import torch
        m = self._ensure_clf(); dev = next(m.parameters()).device
        h, w = bgr.shape[:2]; rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB); S = self.cfg.cls_size
        tiles = [cv2.resize(rgb[y0:y1, x0:x1], (S, S), interpolation=cv2.INTER_LINEAR) for x0, y0, x1, y1 in pp.tile_boxes(h, w, S, S)]
        x = torch.from_numpy(np.stack([pp.normalize_imagenet(t) for t in tiles])).to(dev)
        with torch.no_grad():
            p = torch.sigmoid(m(x).reshape(-1)).cpu().numpy()
        return dict(model_id=IDS["cls"], scope="image", probability=round(float(p.max()), 4), threshold=self.cfg.cls_thr, decision=bool(p.max() >= self.cfg.cls_thr))

    # ---------------- road scene ----------------
    def _road(self, bgr, meta, return_overlay):
        m = self._ensure_rdd(); t0 = time.perf_counter(); H, W = bgr.shape[:2]
        kw = dict(device=self.cfg.device) if self.cfg.device is not None else {}
        r = m.predict(bgr, imgsz=640, conf=self.cfg.rdd_conf, verbose=False, **kw)[0]
        dets = []
        if r.boxes is not None and len(r.boxes):
            xyxy, cf, cl = r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), r.boxes.cls.cpu().numpy().astype(int)
            order = np.argsort(-cf)
            dets = [dict(id=i, box_xyxy=[round(float(max(0, v)), 1) for v in xyxy[j]], confidence=round(float(cf[j]), 4), **{"class": RDD_CLASSES[cl[j]]}, source="yolo") for i, j in enumerate(order)]
        warn = (["NO_DETECTION"] if not dets else []) + [c for c in meta["quality_checks"]["flag_codes"] if c in ("LOW_LIGHT", "POSSIBLE_BLUR")] + (["UNVALIDATED_OPERATING_POINT"] if abs(self.cfg.rdd_conf - RDD_CONF_VALIDATED) > 1e-9 else [])
        severity = sev.assess(None, dets, dict(width=W, height=H), (["NO_YOLO_DETECTION"] if not dets else []) + [w for w in warn if w in ("LOW_LIGHT", "POSSIBLE_BLUR")], self._sev_cfg)
        out = dict(status="ok", schema_version=ROAD_SCHEMA_VERSION, profile="road_scene", pipeline=dict(name="rdd2022_detector", config=dict(conf=self.cfg.rdd_conf, imgsz=640)),
                   models=[self._ref("rdd")], coordinate_frame=dict(width=W, height=H, origin="top-left, x right, y down", resize_scale_to_original=meta["resize_scale"]),
                   detections=dets, class_counts={c: sum(d["class"] == c for d in dets) for c in RDD_CLASSES}, severity=severity, warnings=warn,
                   timing_ms=dict(total_ms=round(1000 * (time.perf_counter() - t0), 2)), disclaimer=DISCLAIMER)
        ov = None
        if return_overlay:
            vis = bgr.copy()
            for d in dets:
                x0, y0, x1, y1 = [int(v) for v in d["box_xyxy"]]; cv2.rectangle(vis, (x0, y0), (x1, y1), (0, 255, 0), 2)
                cv2.putText(vis, f"{d['class']} {d['confidence']:.2f}", (x0, max(14, y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            ov = cv2.imencode(".jpg", vis)[1].tobytes()
        return AnalysisOutput("road_scene", out, meta, None, ov)