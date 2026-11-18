"""
Rule-based damage severity from RELATIVE (pixel-normalised) measurements, driven entirely by a config file.

  weighted score = 100 * sum(weight_i * points_i) / sum(weight_i * max_points_i)   over the features that are available
  category       = cut-points on the score, then optional minimum-category overrides
  output         = category, score, suggested inspection priority, per-feature contributions, flags, explanation

NOT a structural assessment. Thresholds in severity_config.json are placeholders unless config.status == "VALIDATED".
Millimetre features stay inactive until a calibrated mm_per_px AND thresholds are configured (bins != null).
Usage:
    cfg = load_config("ml/severity/severity_config.json")
    out = assess(inference_result["measurements"], detections, image_size=dict(width=640, height=360), warnings=inference_result["warnings"], config=cfg)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ENGINE_VERSION = "severity-0.1"
ORDER = ["NONE", "MINOR", "MODERATE", "SEVERE", "CRITICAL"]
LABELS = {"NONE": "No Visible Damage", "MINOR": "Minor Damage", "MODERATE": "Moderate Damage", "SEVERE": "Severe Damage", "CRITICAL": "Critical / Requires Urgent Engineering Review"}
CLASSES = ["D00", "D10", "D20", "D40"]
DISCLAIMER = "Advisory rating from image-derived relative measures. Visual damage alone does not establish structural integrity; qualified engineering review is required."


class ConfigError(ValueError):
    pass


def validate_config(cfg: dict) -> dict:
    if cfg.get("status") not in ("UNVALIDATED_PLACEHOLDER", "VALIDATED"):
        raise ConfigError("status must be UNVALIDATED_PLACEHOLDER or VALIDATED")
    cuts = cfg.get("score_cuts", {})
    if not (0 < cuts.get("MINOR_max", -1) < cuts.get("MODERATE_max", -1) < cuts.get("SEVERE_max", -1) < 100):
        raise ConfigError("score_cuts must satisfy 0 < MINOR_max < MODERATE_max < SEVERE_max < 100")
    if set(cfg.get("priority_map", {})) != set(ORDER):
        raise ConfigError("priority_map must define exactly " + ", ".join(ORDER))
    ids = set()
    for f in cfg.get("features", []):
        if f["id"] in ids: raise ConfigError(f"duplicate feature {f['id']}")
        ids.add(f["id"])
        if f.get("weight", -1) < 0: raise ConfigError(f"{f['id']}: weight must be >= 0")
        bins = f.get("bins")
        if bins is None: continue
        if not bins or bins[-1]["max"] is not None: raise ConfigError(f"{f['id']}: the last bin must have max=null")
        ups = [b["max"] for b in bins[:-1]]
        if any(u is None for u in ups) or any(b <= a for a, b in zip(ups, ups[1:])): raise ConfigError(f"{f['id']}: bin upper bounds must be strictly increasing")
        pts = [b["points"] for b in bins]
        if any(p < 0 for p in pts) or any(b < a for a, b in zip(pts, pts[1:])): raise ConfigError(f"{f['id']}: points must be >= 0 and non-decreasing")
    for o in cfg.get("overrides", []):
        if o["min_category"] not in ORDER[1:]: raise ConfigError(f"override {o['id']}: bad min_category")
        if o["feature"] not in ids: raise ConfigError(f"override {o['id']}: unknown feature {o['feature']}")
    return cfg


def load_config(path) -> dict:
    return validate_config(json.loads(Path(path).read_text()))


def _points(value, bins):
    for b in bins:
        if b["max"] is None or value < b["max"]:
            return b["points"]
    return bins[-1]["points"]


def _union_share(boxes, W, H, step=4):
    if not boxes: return 0.0
    g = np.zeros((max(1, H // step), max(1, W // step)), bool)
    for x0, y0, x1, y1 in boxes:
        g[int(max(0, y0) // step):int(np.ceil(min(H, y1) / step)), int(max(0, x0) // step):int(np.ceil(min(W, x1) / step))] = True
    return float(g.mean())


def extract_features(measurements, detections, image_size, cfg):
    W, H = image_size["width"], image_size["height"]
    vals = {}
    m = measurements or {}
    if measurements is not None:
        has = m.get("area_px", 0) > 0
        vals["crack_density_percent"] = float(m.get("crack_density_percent", 0.0))
        vals["n_branch_points"] = float(m.get("n_branch_points", 0))
        vals["mean_width_norm640"] = float(m["mean_width_px"]) * cfg["reference_long_side_px"] / max(W, H) if has else None
        if m.get("max_width_mm") is not None: vals["max_width_mm"] = float(m["max_width_mm"])
    if detections is not None:
        for c in CLASSES:
            bx = [d["box_xyxy"] for d in detections if d.get("class") == c]
            vals[f"class_count.{c}"] = float(len(bx)); vals[f"class_area_share.{c}"] = _union_share(bx, W, H)
    return vals


def assess(measurements, detections, image_size, warnings=(), config=None, mm_per_px=None):
    cfg = config or load_config(Path(__file__).with_name("severity_config.json"))
    vals = extract_features(measurements, detections, image_size, cfg)
    calibrated = bool(mm_per_px) or bool((measurements or {}).get("calibration", {}).get("mm_per_px"))
    num = den = 0.0
    contribs, skipped = [], []
    for f in cfg["features"]:
        fid = f["id"]
        if f.get("requires_calibration") and not calibrated: skipped.append(dict(feature=fid, reason="needs a calibrated scale")); continue
        if f.get("bins") is None: skipped.append(dict(feature=fid, reason="thresholds not configured")); continue
        v = vals.get(fid)
        if v is None: skipped.append(dict(feature=fid, reason="input not available")); continue
        p, mp = _points(v, f["bins"]), max(b["points"] for b in f["bins"])
        num += f["weight"] * p; den += f["weight"] * mp
        contribs.append(dict(feature=fid, label=f["label"], value=round(v, 4), points=p, max_points=mp, weight=f["weight"], weighted_points=f["weight"] * p, provenance=f["provenance"]))
    evidence = ((measurements or {}).get("area_px", 0) > 0) or any(vals.get(f"class_count.{c}", 0) > 0 for c in CLASSES)
    score = 100.0 * num / den if den > 0 and evidence else 0.0
    cuts = cfg["score_cuts"]
    cat = "NONE" if (not evidence or score == 0) else "MINOR" if score <= cuts["MINOR_max"] else "MODERATE" if score <= cuts["MODERATE_max"] else "SEVERE" if score <= cuts["SEVERE_max"] else "CRITICAL"
    applied = []
    for o in cfg.get("overrides", []):
        v = vals.get(o["feature"])
        if v is not None and v >= o["gte"] and ORDER.index(o["min_category"]) > ORDER.index(cat):
            cat = o["min_category"]; applied.append(dict(id=o["id"], min_category=o["min_category"], feature=o["feature"], value=round(v, 4), gte=o["gte"]))
    flags = ["RELATIVE_METRICS_ONLY"]
    if cfg["status"] != "VALIDATED": flags.append("THRESHOLDS_NOT_VALIDATED")
    if not calibrated: flags.append("UNCALIBRATED_SCALE")
    if any(w in ("LOW_LIGHT", "POSSIBLE_BLUR") for w in warnings): flags.append("INPUT_QUALITY_WARNING")
    if "NO_YOLO_DETECTION" in warnings: flags.append("DETECTOR_FOUND_NOTHING")
    conf = "LOW" if (cfg["status"] != "VALIDATED" or not calibrated or "INPUT_QUALITY_WARNING" in flags) else "MEDIUM"
    top = sorted(contribs, key=lambda c: -c["weighted_points"])[:3]
    why = "no damage evidence in the inputs" if not evidence else "; ".join(f"{c['label']} = {c['value']} ({c['points']}/{c['max_points']} pts)" for c in top if c["weighted_points"] > 0) or "all measured features score 0"
    expl = f"{LABELS[cat]} (score {score:.1f}/100): {why}." + (" Overrides: " + ", ".join(o["id"] for o in applied) + "." if applied else "")
    if "THRESHOLDS_NOT_VALIDATED" in flags: expl += " Thresholds are unvalidated placeholders."
    if "UNCALIBRATED_SCALE" in flags: expl += " No physical scale: relative measures only."
    return dict(status="ok", engine_version=ENGINE_VERSION, config_id=cfg["config_id"], config_status=cfg["status"], category=cat, label=LABELS[cat], score_0_100=round(score, 2),
                suggested_priority=cfg["priority_map"][cat], engineering_review_required=cat in ("SEVERE", "CRITICAL"), confidence=conf, flags=flags,
                contributions=contribs, skipped_features=skipped, overrides_applied=applied, explanation=expl, disclaimer=DISCLAIMER)
