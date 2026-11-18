"""Tests for image_preprocessing.py. Run:  python ml/preprocessing/test_image_preprocessing.py   (or pytest)."""
import json, sys
from pathlib import Path
import cv2, numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
from image_preprocessing import (ImageValidationError, PreprocessConfig, normalize_imagenet, preprocess_image, tile_boxes)

SCHEMA = Path(__file__).resolve().parents[2] / "docs" / "api_contract" / "preprocessing_result.schema.json"
rng = np.random.RandomState(0)


def enc(img, ext=".jpg"):
    ok, buf = cv2.imencode(ext, img); assert ok; return buf.tobytes()


def textured(h=360, w=640): return rng.randint(0, 256, (h, w, 3), dtype=np.uint8)


def rejected(fn, code):
    try: fn()
    except ImageValidationError as e:
        assert e.code == code, (e.code, code); return e
    raise AssertionError(f"expected {code}")


def test_demo_equivalence():
    """Numbers must equal the demo's own computation (backend/app.py logic, copied here)."""
    img = textured(); raw = enc(img, ".png"); r = preprocess_image(raw, "image/png")
    dec = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR); gray = cv2.cvtColor(dec, cv2.COLOR_BGR2GRAY)
    q = r.meta["quality_checks"]
    assert q["mean_brightness_0_255"] == round(float(np.mean(gray)), 2) and q["laplacian_blur_indicator"] == round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 2)
    assert q["thresholds"] == {"low_light": 45.0, "blur": 60.0} and q["flag_codes"] == [] and q["flags"] == ["No basic low-light/blur warning detected"]


def test_flags():
    dark = preprocess_image(enc(np.full((200, 300, 3), 10, np.uint8)), "image/jpeg").meta["quality_checks"]
    assert dark["flag_codes"] == ["LOW_LIGHT", "POSSIBLE_BLUR"] and "Possible low-light image" in dark["flags"]
    flat = preprocess_image(enc(np.full((200, 300, 3), 128, np.uint8)), "image/jpeg").meta["quality_checks"]
    assert flat["flag_codes"] == ["POSSIBLE_BLUR"]


def test_resize_keeps_aspect_and_records_scale():
    r = preprocess_image(enc(textured(2000, 3000)), "image/jpeg"); d = r.meta["processed_dimensions"]
    assert max(d["width"], d["height"]) == 1280 and abs(d["width"] / d["height"] - 1.5) < 0.01 and abs(r.meta["resize_scale"] - 1280 / 3000) < 1e-5
    assert r.processed_bgr.shape[:2] == (d["height"], d["width"]) and r.original_bgr.shape[:2] == (2000, 3000)
    small = preprocess_image(enc(textured(300, 400)), "image/jpeg"); assert small.meta["resize_scale"] == 1.0 and small.processed_bgr.shape[:2] == (300, 400)


def test_rejections():
    ok = enc(textured())
    rejected(lambda: preprocess_image(b"", "image/jpeg"), "EMPTY_FILE")
    e = rejected(lambda: preprocess_image(ok, "image/jpeg", PreprocessConfig(max_bytes=100)), "FILE_TOO_LARGE"); assert e.http_status == 413
    e = rejected(lambda: preprocess_image(ok, "image/gif"), "UNSUPPORTED_TYPE"); assert e.http_status == 415
    rejected(lambda: preprocess_image(rng.bytes(500), "image/jpeg"), "UNSUPPORTED_TYPE")             # not an image at all
    rejected(lambda: preprocess_image(enc(textured(), ".bmp"), "image/jpeg"), "UNSUPPORTED_TYPE")    # BMP disguised as JPEG
    rejected(lambda: preprocess_image(ok[:200], "image/jpeg"), "DECODE_FAILED")                      # truncated JPEG
    rejected(lambda: preprocess_image(enc(textured(40, 500)), "image/jpeg"), "IMAGE_TOO_SMALL")
    assert preprocess_image(enc(textured(), ".bmp"), "image/jpeg", PreprocessConfig(sniff_format=False)).meta["status"] == "ok"   # demo-compatible mode


def test_blur_normalisation_is_optional_and_changes_value():
    raw = enc(textured(1000, 1500)); a = preprocess_image(raw, "image/jpeg").meta["quality_checks"]["laplacian_blur_indicator"]
    b = preprocess_image(raw, "image/jpeg", PreprocessConfig(blur_normalize_side=640)).meta["quality_checks"]["laplacian_blur_indicator"]
    assert a != b


def test_tiles_cover_image():
    for h, w in ((1440, 2560), (800, 1100), (500, 3000)):
        cov = np.zeros((h, w), bool)
        for x0, y0, x1, y1 in tile_boxes(h, w): assert 0 <= x0 < x1 <= w and 0 <= y0 < y1 <= h; cov[y0:y1, x0:x1] = True
        assert cov.all()


def test_normalisation_matches_training_formula():
    x = textured(32, 32); n = normalize_imagenet(x)
    assert n.shape == (3, 32, 32) and n.dtype == np.float32 and abs(n[0, 0, 0] - ((x[0, 0, 0] / 255 - 0.485) / 0.229)) < 1e-5


def test_output_matches_json_schema():
    try: import jsonschema
    except ImportError: print("jsonschema not installed: schema test skipped"); return
    schema = json.loads(SCHEMA.read_text())
    jsonschema.validate(preprocess_image(enc(textured()), "image/jpeg").to_dict(), schema)
    jsonschema.validate(preprocess_image(enc(textured()), None).to_dict(), schema)                    # no declared type
    jsonschema.validate(rejected(lambda: preprocess_image(b"", "image/png"), "EMPTY_FILE").to_dict(), schema)
    try: jsonschema.validate({"status": "ok"}, schema); raise AssertionError("invalid doc accepted")
    except jsonschema.ValidationError: pass


if __name__ == "__main__":
    for n in [n for n in dir() if n.startswith("test_")]: globals()[n](); print("PASS", n)
