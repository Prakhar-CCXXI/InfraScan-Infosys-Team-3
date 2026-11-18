"""
Evaluate a trained RDD2022 detector with Ultralytics val: overall and PER-CLASS precision, recall, mAP50, mAP50-95,
plus the number of ground-truth boxes per class so unreliable classes are flagged (fewer than --min-boxes).

  python ml/detection/eval_rdd2022_yolo.py --weights <best.pt> --dataset-root /content/rdd2022_yolo --split val
  python ml/detection/eval_rdd2022_yolo.py --weights <best.pt> --dataset-root /content/rdd2022_yolo --split test    # ONE-SHOT: refuses a second run unless --force
Run val first and choose everything on val. The test run is for reporting only.
"""
import argparse, hashlib, json
from pathlib import Path

NAMES = ["D00", "D10", "D20", "D40"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def count_boxes(root: Path, split: str):
    n = dict.fromkeys(NAMES, 0)
    for t in (root / "labels" / split).glob("*.txt"):
        for ln in t.read_text().split("\n"):
            if ln.strip():
                n[NAMES[int(ln.split()[0])]] += 1
    return n


def summarize(r, names, n_boxes, min_boxes):
    idx = [int(i) for i in r.box.ap_class_index]
    per = {}
    for j, c in enumerate(idx):
        nm = names[c]
        per[nm] = dict(precision=float(r.box.p[j]), recall=float(r.box.r[j]), mAP50=float(r.box.ap50[j]), mAP50_95=float(r.box.ap[j]),
                       gt_boxes=n_boxes[nm], reliable=n_boxes[nm] >= min_boxes)
    for nm in NAMES:   # classes absent from predictions/GT still reported
        per.setdefault(nm, dict(precision=None, recall=None, mAP50=None, mAP50_95=None, gt_boxes=n_boxes[nm], reliable=n_boxes[nm] >= min_boxes))
    return dict(overall=dict(precision=float(r.box.mp), recall=float(r.box.mr), mAP50=float(r.box.map50), mAP50_95=float(r.box.map)), per_class=per)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--split", choices=["val", "test"], default="val")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--min-boxes", type=int, default=30)
    ap.add_argument("--out-dir", default=None)
    ap.add_argument("--device", default="0")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    root = Path(a.dataset_root); out = Path(a.out_dir) if a.out_dir else Path(a.weights).resolve().parents[1]
    res_path = out / f"rdd2022_{a.split}_metrics.json"
    if a.split == "test" and res_path.exists() and not a.force:
        raise SystemExit(f"{res_path} exists: the test split was already evaluated for these weights. Use --force only deliberately.")
    from ultralytics import YOLO
    model = YOLO(a.weights)
    r = model.val(data=str(root / "rdd2022_damage_local.yaml"), split=a.split, imgsz=a.imgsz, batch=a.batch, device=a.device, plots=True,
                  project=str(out), name=f"val_{a.split}", exist_ok=True)
    n = count_boxes(root, a.split)
    res = dict(weights=a.weights, weights_sha256=sha256(a.weights), split=a.split, imgsz=a.imgsz, gt_boxes=n, **summarize(r, model.names, n, a.min_boxes),
               note=f"classes with fewer than {a.min_boxes} ground-truth boxes are flagged reliable=false; use val only for choices, test only for reporting")
    res_path.write_text(json.dumps(res, indent=2)); print(json.dumps(res, indent=2)); print("saved", res_path)


if __name__ == "__main__":
    main()
