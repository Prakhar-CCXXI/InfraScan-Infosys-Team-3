"""Tests for inference_service.py with FAKE models (no torch/ultralytics).  Run: python ml/service/test_inference_service.py   (needs jsonschema)"""
import json, sys, tempfile, hashlib
from pathlib import Path
import cv2, jsonschema, numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import inference_service as IS
from hybrid_pipeline import HybridConfig

API = HERE.parents[1] / "docs" / "api_contract"
V = lambda n: jsonschema.Draft7Validator(json.loads((API / n).read_text()))
CLOSE, ROAD, PRE, SEV = V("inference_result.schema.json"), V("road_scene_result.schema.json"), V("preprocessing_result.schema.json"), V("severity_result.schema.json")
rng = np.random.RandomState(0)


def jpg(h=360, w=640): return cv2.imencode(".jpg", rng.randint(0, 255, (h, w, 3), dtype=np.uint8))[1].tobytes()
def ok(v, d): errs = list(v.iter_errors(d)); assert not errs, errs[0].message[:200]


class FakeYolo:
    names = {0: "D00", 1: "D10", 2: "D20", 3: "D40"}
    def __init__(s, dets=()): s.dets = dets
    def predict(s, bgr, **kw):
        class T:
            def __init__(s, a): s.a = np.array(a)
            def cpu(s): return s
            def numpy(s): return s.a
        class B:
            def __init__(b, d): b.xyxy, b.conf, b.cls = T([x[:4] for x in d] or np.zeros((0, 4))), T([x[4] for x in d]), T([x[5] for x in d])
            def __len__(b): return len(b.conf.a)
        class R: pass
        r = R(); r.boxes = B(s.dets); return [r]


class FakePipe:
    def __init__(s, with_yolo=True): s.yolo = object() if with_yolo else None
    def sync(s): pass
    def unet_prob(s, rgb): p = np.zeros(rgb.shape[:2], np.float32); p[100:110, 100:500] = 0.95; return p
    def predict(s, bgr, cfg, measure=True):
        from geometry import crack_geometry
        m = np.zeros(bgr.shape[:2], np.uint8); m[100:110, 100:500] = 1
        return dict(mode="full_image_dual_threshold", image_size=dict(width=bgr.shape[1], height=bgr.shape[0]), yolo_detected=True, boxes=[dict(xyxy=[90, 90, 510, 120], conf=0.8)],
                    yolo_mask=m, hybrid_mask=m, hybrid_prob=None, timing_ms=dict(yolo_ms=10.0, unet_fuse_ms=30.0, total_ms=40.0),
                    config=dict(yolo_conf=0.1, gate="mask", margin=8, t_in=0.4, t_out=0.9), measurements=crack_geometry(m))


def svc(**kw):
    s = IS.InferenceService(IS.ServiceConfig(**kw))
    s._hybrid_cfg = HybridConfig(yolo_conf=0.1, gate="mask", margin=8, t_in=0.4, t_out=0.9)
    s.loaded = {IS.IDS["unet"]: "a" * 64, IS.IDS["yolo"]: "b" * 64, IS.IDS["rdd"]: "c" * 64, IS.IDS["cls"]: "d" * 64}
    return s


def test_close_up_hybrid_and_unet_only():
    s = svc(); s._pipe = FakePipe(True); o = s.analyze(jpg(), "image/jpeg")
    ok(CLOSE, o.result); ok(PRE, o.preprocessing); ok(SEV, o.result["severity"]); assert o.result["pipeline"]["name"] == "hybrid_dual_threshold" and o.result["detections"]
    assert cv2.imdecode(np.frombuffer(o.mask_png, np.uint8), 0).max() == 255 and cv2.imdecode(np.frombuffer(o.overlay_jpg, np.uint8), 1) is not None
    s2 = svc(); s2._pipe = FakePipe(False); s2._hybrid_cfg = None; o2 = s2.analyze(jpg(), "image/jpeg", return_overlay=False)
    ok(CLOSE, o2.result); assert o2.result["pipeline"]["name"] == "unet_only" and o2.result["detections"] == [] and o2.overlay_jpg is None and len(o2.result["models"]) == 1


def test_close_up_calibration_and_flags():
    s = svc(); s._pipe = FakePipe(True); o = s.analyze(jpg(), "image/jpeg", mm_per_px=0.5, calibration_source="ruler in frame")
    ok(CLOSE, o.result); assert o.result["measurements"]["unit"] == "mm" and "UNCALIBRATED_SCALE" not in o.result["severity"]["flags"]
    o = s.analyze(jpg(), "image/jpeg"); assert "UNCALIBRATED_SCALE" in o.result["severity"]["flags"] and "PIXEL_UNITS_ONLY" in o.result["warnings"]


def test_classification_option():
    s = svc(); s._pipe = FakePipe(True)
    class Clf: pass
    s._classify = lambda bgr: dict(model_id=IS.IDS["cls"], scope="image", probability=0.9, threshold=0.5058, decision=True)
    o = s.analyze(jpg(), "image/jpeg", classify=True); ok(CLOSE, o.result); assert o.result["classification"]["decision"] and o.result["models"][-1]["role"] == "classification"
    assert "classification" not in s.analyze(jpg(), "image/jpeg").result


def test_road_scene():
    s = svc(); s._rdd = FakeYolo([(10, 20, 200, 120, 0.7, 2), (300, 200, 360, 260, 0.9, 3), (5, 5, 50, 50, 0.4, 0)]); o = s.analyze(jpg(720, 720), "image/jpeg", profile="road_scene")
    ok(ROAD, o.result); ok(PRE, o.preprocessing); ok(SEV, o.result["severity"]); r = o.result
    assert r["class_counts"] == {"D00": 1, "D10": 0, "D20": 1, "D40": 1} and r["detections"][0]["confidence"] == 0.9 and "UNVALIDATED_OPERATING_POINT" not in r["warnings"] and o.mask_png is None and r["pipeline"]["config"]["conf"] == IS.RDD_CONF_VALIDATED == 0.233
    so = svc(rdd_conf=0.5); so._rdd = FakeYolo([(10, 20, 200, 120, 0.7, 2)]); ro = so.analyze(jpg(720, 720), "image/jpeg", profile="road_scene").result
    ok(ROAD, ro); assert "UNVALIDATED_OPERATING_POINT" in ro["warnings"] and ro["pipeline"]["config"]["conf"] == 0.5   # an override is flagged
    s0 = svc(); s0._rdd = FakeYolo([]); r0 = s0.analyze(jpg(720, 720), "image/jpeg", profile="road_scene").result
    ok(ROAD, r0); assert r0["severity"]["category"] == "NONE" and "NO_DETECTION" in r0["warnings"] and "DETECTOR_FOUND_NOTHING" in r0["severity"]["flags"]


def test_errors():
    s = svc(); s._pipe = FakePipe(True)
    for bad, code in ((lambda: s.analyze(jpg(), "image/jpeg", profile="x"), "INVALID_INPUT"), (lambda: s.analyze(jpg(), "image/jpeg", mm_per_px=0.5), "INVALID_INPUT")):
        try: bad(); raise AssertionError("accepted")
        except IS.ServiceError as e: assert e.code == code and e.http_status == 400 and e.to_dict()["status"] == "error"
    for raw, ct, code in ((b"", "image/jpeg", "EMPTY_FILE"), (b"notanimage" * 20, "image/jpeg", "UNSUPPORTED_TYPE"), (jpg(40, 500), "image/jpeg", "IMAGE_TOO_SMALL")):
        try: s.analyze(raw, ct); raise AssertionError("accepted")
        except IS.pp.ImageValidationError as e: assert e.code == code
    class Boom(FakePipe):
        def predict(s, *a, **k): raise RuntimeError("cuda out of memory")
    b = svc(); b._pipe = Boom()
    try: b.analyze(jpg(), "image/jpeg"); raise AssertionError("no error")
    except IS.ServiceError as e: assert e.code == "INFERENCE_FAILED" and "cuda out of memory" in e.message and e.http_status == 500


def test_checkpoint_missing_and_hash_verification():
    d = Path(tempfile.mkdtemp()); f = d / "m.pt"; f.write_bytes(b"weights"); good = hashlib.sha256(b"weights").hexdigest()
    def reg(h): p = d / "r.json"; p.write_text(json.dumps(dict(models=[dict(id=IS.IDS["unet"], checkpoint=dict(sha256=h))]))); return str(p)
    s = IS.InferenceService(IS.ServiceConfig(unet_ckpt=str(f), registry=reg(good))); assert s._verify("unet", str(f)) == good and s.loaded[IS.IDS["unet"]] == good
    for cfg, want in ((IS.ServiceConfig(unet_ckpt=str(f), registry=reg("0" * 64)), "checksum"), (IS.ServiceConfig(unet_ckpt=str(d / "nope.pt")), "not found")):
        try: IS.InferenceService(cfg)._verify("unet", cfg.unet_ckpt); raise AssertionError("accepted")
        except IS.ServiceError as e: assert e.code == "MODEL_UNAVAILABLE" and want in e.message and e.http_status == 503
    s2 = IS.InferenceService(IS.ServiceConfig(unet_ckpt=str(f), registry=reg("NEEDS VERIFICATION"))); s2._verify("unet", str(f)); assert s2.loaded[IS.IDS["unet"]] == "" and s2._ref("unet")["sha256"] is None
    s3 = IS.InferenceService(IS.ServiceConfig(unet_ckpt=str(f), registry=reg("0" * 64), verify_hashes=False)); s3._verify("unet", str(f))   # opt-out works


def test_health_and_env():
    s = svc(); h = s.health(); assert h["severity_config"]["status"] == "UNVALIDATED_PLACEHOLDER" and len(h["loaded_models"]) == 4
    c = IS.ServiceConfig.from_env(); assert c.verify_hashes is True


if __name__ == "__main__":
    for n in [n for n in dir() if n.startswith("test_")]: globals()[n](); print("PASS", n)
