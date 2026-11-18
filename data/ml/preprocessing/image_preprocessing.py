"""
Reusable image validation, quality assessment and pre-processing for InfraScan AI models.

Defaults reproduce the existing FastAPI demo (backend/app.py), which is left untouched:
  JPEG/PNG/WebP, 10 MB limit, minimum side 64 px, low-light if mean grayscale < 45,
  possible blur if Laplacian variance < 60, longest side capped at 1280 px (aspect ratio preserved).
Quality flags are ADVISORY. The Laplacian rule measures texture as well as blur and depends on resolution
(smooth, uncracked concrete scores low); `blur_normalize_side` offers a resolution-normalised variant (off by default).

Additions over the demo (documented, all optional via PreprocessConfig):
  * content sniffing (magic bytes) in addition to the declared content type  (sniff_format=True)
  * SHA-256 of the uploaded bytes (for duplicate detection / audit trail)
  * tiling helpers and ImageNet normalisation shared with the model code
No web-framework dependency: failures raise ImageValidationError(code, message, http_status).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

MODULE_VERSION = "preprocessing-0.1"
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)   # same normalisation as train_seg.py / hybrid_pipeline.py
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)
_MIME = {"jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


class ImageValidationError(Exception):
    """code: EMPTY_FILE | FILE_TOO_LARGE | UNSUPPORTED_TYPE | DECODE_FAILED | IMAGE_TOO_SMALL"""
    def __init__(self, code: str, message: str, http_status: int = 400):
        super().__init__(message)
        self.code, self.message, self.http_status = code, message, http_status

    def to_dict(self):
        return {"status": "rejected", "error": {"code": self.code, "message": self.message, "http_status": self.http_status}}


@dataclass(frozen=True)
class PreprocessConfig:
    allowed_types: tuple = ("image/jpeg", "image/png", "image/webp")
    max_bytes: int = 10 * 1024 * 1024
    min_dimension: int = 64
    low_light_threshold: float = 45.0
    blur_threshold: float = 60.0
    max_side: int = 1280
    sniff_format: bool = True
    blur_normalize_side: int | None = None      # e.g. 640: compute the blur indicator on a fixed-size copy


@dataclass
class PreprocessResult:
    original_bgr: np.ndarray
    processed_bgr: np.ndarray
    scale: float
    meta: dict = field(default_factory=dict)

    @property
    def processed_rgb(self):
        return cv2.cvtColor(self.processed_bgr, cv2.COLOR_BGR2RGB)

    def to_dict(self):
        """JSON-safe metadata (no arrays); matches docs/api_contract/preprocessing_result.schema.json"""
        return dict(self.meta)


def sniff_format(raw: bytes):
    if raw[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    return None


def quality_indicators(bgr, cfg: PreprocessConfig = PreprocessConfig()):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    g = gray
    if cfg.blur_normalize_side:
        s = cfg.blur_normalize_side / float(max(gray.shape))
        g = cv2.resize(gray, (max(1, int(gray.shape[1] * s)), max(1, int(gray.shape[0] * s))), interpolation=cv2.INTER_AREA)
    blur = float(cv2.Laplacian(g, cv2.CV_64F).var())
    codes, texts = [], []
    if brightness < cfg.low_light_threshold:
        codes.append("LOW_LIGHT"); texts.append("Possible low-light image")
    if blur < cfg.blur_threshold:
        codes.append("POSSIBLE_BLUR"); texts.append("Possible blur — inspect image manually")
    if not texts:
        texts.append("No basic low-light/blur warning detected")
    return brightness, blur, codes, texts


def preprocess_image(raw: bytes, content_type: str | None = None, config: PreprocessConfig = PreprocessConfig()) -> PreprocessResult:
    cfg = config
    if content_type is not None and content_type not in cfg.allowed_types:
        raise ImageValidationError("UNSUPPORTED_TYPE", "Unsupported image type. Upload JPG, PNG, or WEBP.", 415)
    if not raw:
        raise ImageValidationError("EMPTY_FILE", "The uploaded file is empty.", 400)
    if len(raw) > cfg.max_bytes:
        raise ImageValidationError("FILE_TOO_LARGE", f"File exceeds the {cfg.max_bytes // (1024 * 1024)} MB limit.", 413)
    fmt = sniff_format(raw)
    if cfg.sniff_format and (fmt is None or _MIME[fmt] not in cfg.allowed_types):
        raise ImageValidationError("UNSUPPORTED_TYPE", "File content is not a JPEG, PNG or WEBP image.", 415)
    bgr = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)    # OpenCV applies EXIF orientation by default
    if bgr is None:
        raise ImageValidationError("DECODE_FAILED", "File could not be decoded as a valid image.", 400)
    h, w = bgr.shape[:2]
    if min(h, w) < cfg.min_dimension:
        raise ImageValidationError("IMAGE_TOO_SMALL", f"Image is too small (minimum dimension: {cfg.min_dimension} px).", 400)

    brightness, blur, codes, texts = quality_indicators(bgr, cfg)
    scale = min(1.0, cfg.max_side / float(max(h, w)))
    tw, th = max(1, int(w * scale)), max(1, int(h * scale))
    processed = bgr if scale == 1.0 else cv2.resize(bgr, (tw, th), interpolation=cv2.INTER_AREA)
    steps = ["decoded image (EXIF orientation applied by OpenCV)", "grayscale quality indicators calculated",
             "aspect ratio preserved", f"longest side limited to {cfg.max_side} px"]
    meta = dict(
        status="ok", module_version=MODULE_VERSION,
        file=dict(size_bytes=len(raw), declared_content_type=content_type, detected_format=fmt, sha256=hashlib.sha256(raw).hexdigest()),
        original_dimensions=dict(width=w, height=h), processed_dimensions=dict(width=tw, height=th), resize_scale=round(scale, 6),
        quality_checks=dict(mean_brightness_0_255=round(brightness, 2), laplacian_blur_indicator=round(blur, 2), flags=texts, flag_codes=codes,
                            thresholds=dict(low_light=cfg.low_light_threshold, blur=cfg.blur_threshold), blur_normalize_side=cfg.blur_normalize_side),
        preprocessing=steps)
    return PreprocessResult(original_bgr=bgr, processed_bgr=processed, scale=scale, meta=meta)


def preprocess_path(path, config: PreprocessConfig = PreprocessConfig()) -> PreprocessResult:
    """Convenience for scripts/notebooks: infer the declared type from the file extension."""
    p = Path(path)
    ct = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(p.suffix.lower())
    return preprocess_image(p.read_bytes(), ct, config)


# ---------------- shared helpers for model code ----------------
def normalize_imagenet(rgb_uint8: np.ndarray) -> np.ndarray:
    """uint8 HxWx3 RGB -> float32 3xHxW, (x/255 - mean)/std (identical to the segmentation/classification training code)."""
    return ((rgb_uint8.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1).copy()


def needs_tiling(h: int, w: int, limit: int = 1024) -> bool:
    return max(h, w) > limit


def tile_boxes(h: int, w: int, tile: int = 768, stride: int = 512):
    """Overlapping tile boxes (x0, y0, x1, y1) covering the image; same logic as hybrid_pipeline._unet_run."""
    th, tw = min(tile, h), min(tile, w)
    ys = sorted(set(list(range(0, h - th + 1, stride)) + [h - th]))
    xs = sorted(set(list(range(0, w - tw + 1, stride)) + [w - tw]))
    return [(x, y, x + tw, y + th) for y in ys for x in xs]
