"""
Crack500 binary masks -> Ultralytics YOLO-seg dataset. The OFFICIAL split in the manifest is preserved.
Also writes: conversion_report.json (polygon fidelity), split_leak_flags.csv (leakage audit), check/*.jpg (visual check).

Usage:
  python prepare_yolo_dataset.py --manifest /kaggle/working/crack500_manifest.csv --out-dir /kaggle/working/yolo_crack500
"""
import argparse, hashlib, json, shutil
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def mask_to_polygons(mask, eps=0.7, min_size=6):
    """Binary mask -> (list of Nx2 float32 pixel polygons, n_dropped_components).
    External contours only (holes are filled). Components whose bbox side < min_size px are dropped."""
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polys, dropped = [], 0
    for c in cnts:
        _, _, w, h = cv2.boundingRect(c)
        if max(w, h) < min_size:
            dropped += 1
            continue
        a = cv2.approxPolyDP(c, eps, True).reshape(-1, 2)
        if len(a) < 3:                                   # degenerate 1-px line: use its min-area rectangle
            a = cv2.boxPoints(cv2.minAreaRect(c))
        polys.append(a.astype(np.float32))
    return polys, dropped


def polygons_to_mask(polys, shape):
    out = np.zeros(shape, np.uint8)
    for p in polys:
        cv2.fillPoly(out, [np.round(p).astype(np.int32)], 1)
    return out


def to_yolo_lines(polys, W, H):
    return ["0 " + " ".join(f"{v:.6f}" for v in np.clip(p / np.array([W, H], np.float32), 0, 1).reshape(-1))
            for p in polys]


def iou(a, b):
    u = int(((a > 0) | (b > 0)).sum())
    return 1.0 if u == 0 else int(((a > 0) & (b > 0)).sum()) / u


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", default="/kaggle/working/yolo_crack500")
    ap.add_argument("--eps", type=float, default=0.7, help="approxPolyDP epsilon in px (small = keeps thin cracks)")
    ap.add_argument("--min-size", type=int, default=6, help="drop components with bbox max side below this (px)")
    ap.add_argument("--n-check", type=int, default=16, help="overlay images for visual validation")
    a = ap.parse_args()
    out = Path(a.out_dir)
    m = pd.read_csv(a.manifest)
    assert {"split", "stem", "img_path", "mask_path"} <= set(m.columns)
    assert not m.duplicated(["split", "stem"]).any(), "duplicate stem inside one split"

    for sp in ("train", "val", "test"):
        (out / "images" / sp).mkdir(parents=True, exist_ok=True)
        (out / "labels" / sp).mkdir(parents=True, exist_ok=True)
    (out / "check").mkdir(exist_ok=True)

    rows, ious, n_inst, n_drop, n_empty = [], [], 0, 0, 0
    rng = np.random.RandomState(0)
    check_ids = set(rng.choice(len(m), min(a.n_check, len(m)), replace=False).tolist())
    for i, r in m.iterrows():
        img = cv2.imread(r.img_path); H, W = img.shape[:2]
        gt = cv2.imread(r.mask_path, cv2.IMREAD_UNCHANGED); gt = (gt[..., 0] if gt.ndim == 3 else gt) > 0
        assert gt.shape == (H, W), f"size mismatch {r.stem}"
        polys, dropped = mask_to_polygons(gt.astype(np.uint8), a.eps, a.min_size)
        n_inst += len(polys); n_drop += dropped; n_empty += int(len(polys) == 0)
        ext = Path(r.img_path).suffix.lower()
        dst = out / "images" / r.split / f"{r.stem}{ext}"
        shutil.copy2(r.img_path, dst)                      # copy (not symlink): Ultralytics resolves labels from this path
        (out / "labels" / r.split / f"{r.stem}.txt").write_text("\n".join(to_yolo_lines(polys, W, H)))
        rec = polygons_to_mask(polys, (H, W)); ious.append(iou(rec, gt))
        rows.append(dict(split=r.split, stem=r.stem, md5=hashlib.md5(dst.read_bytes()).hexdigest()))
        if i in check_ids:
            vis = img.copy()
            cnts, _ = cv2.findContours(gt.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            cv2.drawContours(vis, cnts, -1, (0, 255, 0), 1)                                      # GT mask outline: green
            for p in polys: cv2.polylines(vis, [np.round(p).astype(np.int32)], True, (0, 0, 255), 1)  # YOLO polygon: red
            cv2.imwrite(str(out / "check" / f"{r.split}_{r.stem}.jpg"), np.hstack([img, vis]))

    ious = np.array(ious)
    # ---- leakage audit (official split is kept; this only reports) ----
    f = pd.DataFrame(rows)
    t = f.stem.str.split("_")
    f["source_group"] = t.str[0] + "_" + t.str[1]                  # assumed source photo = date_time prefix
    shared_src = f.groupby("source_group").split.nunique()
    shared_md5 = f.groupby("md5").split.nunique()
    f["shared_source_group"] = f.source_group.isin(shared_src[shared_src > 1].index)
    f["shared_exact_image"] = f.md5.isin(shared_md5[shared_md5 > 1].index)
    f["shared_stem"] = f.duplicated("stem", keep=False)
    f["leak_flag"] = f.shared_source_group | f.shared_exact_image | f.shared_stem
    f.drop(columns="md5").to_csv(out / "split_leak_flags.csv", index=False)

    (out / "crack500_yolo.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n  0: crack\n")
    rep = dict(images=len(m), split_counts=m.split.value_counts().to_dict(), polygons=int(n_inst),
               dropped_tiny_components=int(n_drop), images_without_polygons=int(n_empty),
               polygon_vs_mask_iou=dict(mean=float(ious.mean()), p05=float(np.percentile(ious, 5)), min=float(ious.min()),
                                        share_below_0_8=float((ious < 0.8).mean())),
               leakage_audit=dict(
                   source_groups=int(f.source_group.nunique()),
                   groups_spanning_splits=int((shared_src > 1).sum()),
                   exact_duplicate_images_across_splits=int((shared_md5 > 1).sum()),
                   stems_shared_across_splits=int(f.stem.duplicated().sum()),
                   flagged_images_per_split=f[f.leak_flag].split.value_counts().to_dict()),
               note="polygon_vs_mask_iou is an UPPER BOUND on YOLO mask quality (label conversion loss only).")
    (out / "conversion_report.json").write_text(json.dumps(rep, indent=2))
    print(json.dumps(rep, indent=2)); print("YAML:", out / "crack500_yolo.yaml")


if __name__ == "__main__":
    main()
