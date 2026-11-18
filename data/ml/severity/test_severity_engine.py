"""Tests for severity_engine.py.  Run: python ml/severity/test_severity_engine.py   (needs: pip install jsonschema)"""
import copy, json, sys
from pathlib import Path
import jsonschema
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
import severity_engine as S

API = HERE.parents[1] / "docs" / "api_contract"
CFG = S.load_config(HERE / "severity_config.json"); IMG = dict(width=640, height=360)
RES_SCHEMA = json.loads((API / "severity_result.schema.json").read_text()); CFG_SCHEMA = json.loads((API / "severity_config.schema.json").read_text())


def meas(dens=1.0, w=20.0, br=2, area=3000, **kw):
    return dict(area_px=area, crack_density_percent=dens, mean_width_px=w, max_width_px=w * 1.5, n_branch_points=br, length_px=300, calibration=dict(mm_per_px=None, source=None), **kw)


def a(m, det=None, cfg=CFG, **kw): return S.assess(m, det, IMG, kw.pop("warnings", []), cfg, **kw)


def test_config_valid_against_schema_and_code():
    jsonschema.validate(json.loads((HERE / "severity_config.json").read_text()), CFG_SCHEMA); S.validate_config(copy.deepcopy(CFG))


def test_no_evidence_is_none():
    r = a(meas(0, 0, 0, area=0), []); assert r["category"] == "NONE" and r["score_0_100"] == 0 and r["suggested_priority"] == "Routine Monitoring"
    assert S.assess(None, [], IMG, [], CFG)["category"] == "NONE"


def test_monotone_in_each_feature():
    for name, grid in (("dens", [0, .1, .5, 1, 2, 5, 10, 30]), ("w", [3, 10, 16, 20, 30, 60]), ("br", [0, 2, 5, 10, 30])):
        prev = (-1, -1)
        for v in grid:
            r = a(meas(**{name: v})); cur = (r["score_0_100"], S.ORDER.index(r["category"])); assert cur[0] >= prev[0] and cur[1] >= prev[1], (name, v, cur, prev); prev = cur
    prev = -1
    for share in (0, .01, .03, .1, .25, .5):
        side = (share * 640 * 360) ** .5; r = a(None, [dict(box_xyxy=[0, 0, side, side], **{"class": "D20"})]); assert r["score_0_100"] >= prev; prev = r["score_0_100"]


def test_mid_range_is_moderate_and_extremes_are_extreme():
    assert a(meas(2.2, 20, 4))["category"] == "MODERATE"
    assert a(meas(0.3, 5, 0))["category"] == "MINOR"
    assert S.ORDER.index(a(meas(20, 80, 40))["category"]) >= 3


def test_override_and_detection_features():
    big = [dict(box_xyxy=[0, 0, 640, 140], **{"class": "D20"})]            # about 39% of the image
    r = a(None, big); assert S.ORDER.index(r["category"]) >= 3 and r["overrides_applied"][0]["id"] == "large_alligator_area" and r["engineering_review_required"]
    assert any(c["feature"] == "class_count.D20" or c["feature"].startswith("class_area") for c in r["contributions"])
    r2 = a(meas(), None); assert any(s["feature"].startswith("class_area") and s["reason"] == "input not available" for s in r2["skipped_features"])


def test_flags_confidence_and_calibration_gate():
    r = a(meas()); assert {"UNCALIBRATED_SCALE", "THRESHOLDS_NOT_VALIDATED", "RELATIVE_METRICS_ONLY"} <= set(r["flags"]) and r["confidence"] == "LOW"
    assert any(s["feature"] == "max_width_mm" and s["reason"] == "needs a calibrated scale" for s in r["skipped_features"])
    c = copy.deepcopy(CFG); c["status"] = "VALIDATED"
    for f in c["features"]:
        if f["id"] == "max_width_mm": f["bins"] = [dict(max=0.3, points=0), dict(max=1.0, points=2), dict(max=None, points=4)]
    cal = meas(max_width_mm=1.5); cal["calibration"] = dict(mm_per_px=0.5, source="ruler")
    r = a(cal, None, c); assert r["confidence"] == "MEDIUM" and "UNCALIBRATED_SCALE" not in r["flags"] and "THRESHOLDS_NOT_VALIDATED" not in r["flags"] and any(x["feature"] == "max_width_mm" for x in r["contributions"])
    assert a(cal, None, c, warnings=["POSSIBLE_BLUR"])["confidence"] == "LOW"


def test_invalid_configs_rejected():
    def bad(mut):
        c = copy.deepcopy(CFG); mut(c)
        try: S.validate_config(c)
        except S.ConfigError: return
        raise AssertionError("accepted")
    bad(lambda c: c["features"][0]["bins"].__setitem__(1, dict(max=0.1, points=1)))          # bounds not increasing
    bad(lambda c: c["features"][0]["bins"][-1].update(max=9))                                 # last bin not open
    bad(lambda c: c["features"][0]["bins"][2].update(points=0))                               # points decrease
    bad(lambda c: c["features"][0].update(weight=-1)); bad(lambda c: c["overrides"][0].update(feature="nope"))
    bad(lambda c: c["score_cuts"].update(MINOR_max=60)); bad(lambda c: c.update(status="OK"))


def test_results_match_schema():
    for r in (a(meas()), a(meas(0, 0, 0, area=0), []), a(None, [dict(box_xyxy=[0, 0, 640, 140], **{"class": "D20"})]), a(meas(30, 80, 40), warnings=["LOW_LIGHT"])):
        jsonschema.validate(r, RES_SCHEMA)


def test_inference_schema_still_accepts_old_documents_and_new_optional_fields():
    sch = jsonschema.Draft7Validator(json.loads((API / "inference_result.schema.json").read_text())); ex = json.loads((API / "inference_result.example.json").read_text())
    assert not list(sch.iter_errors(ex))
    ex["detections"][0]["class"] = "D20"; ex["severity"] = a(meas()); assert not list(sch.iter_errors(ex))
    ex["detections"][0]["class"] = "D99"; assert list(sch.iter_errors(ex))


if __name__ == "__main__":
    for n in [n for n in dir() if n.startswith("test_")]: globals()[n](); print("PASS", n)
