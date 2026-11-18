"""
Train a YOLO11 detector on the converted RDD2022 India dataset (classes D00, D10, D20, D40).
Uses the TRAIN split only; Ultralytics picks best.pt on the VAL split. The test split is never touched here.

Colab (T4):   pip install ultralytics
  python ml/detection/train_rdd2022_yolo.py --dataset-root /content/rdd2022_yolo --project /content/drive/MyDrive/InfraScan_rdd2022
Put --project on Google Drive so weights/last.pt survives a runtime drop; keep the dataset on /content (fast local disk).
RESUME: run the SAME command again; if <project>/<name>/weights/last.pt exists, training resumes from it.
Optional: --time-hours 2.5 makes Ultralytics fit the whole schedule into that wall-clock budget.
"""
import argparse, hashlib
from pathlib import Path

NAMES = ["D00", "D10", "D20", "D40"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def check_dataset(root: Path):
    """Fail early on a broken dataset; returns counts."""
    out = {}
    for sp in ("train", "val", "test"):
        imgs = {p.stem for p in (root / "images" / sp).glob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}}
        labs = {p.stem for p in (root / "labels" / sp).glob("*.txt")}
        assert imgs and imgs == labs, f"{sp}: {len(imgs)} images vs {len(labs)} label files"
        boxes = [0] * len(NAMES)
        for t in (root / "labels" / sp).glob("*.txt"):
            for ln in t.read_text().split("\n"):
                if ln.strip():
                    c = int(ln.split()[0]); assert 0 <= c < len(NAMES), f"bad class id {c} in {t.name}"; boxes[c] += 1
        out[sp] = dict(images=len(imgs), boxes=dict(zip(NAMES, boxes)))
    return out


def write_yaml(root: Path) -> Path:
    y = root / "rdd2022_damage_local.yaml"
    y.write_text(f"path: {root.resolve().as_posix()}\ntrain: images/train\nval: images/val\ntest: images/test\nnames:\n" + "".join(f"  {i}: {n}\n" for i, n in enumerate(NAMES)))
    return y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset-root", required=True)
    ap.add_argument("--model", default="yolo11s.pt")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--patience", type=int, default=15)
    ap.add_argument("--time-hours", type=float, default=None)
    ap.add_argument("--project", default="/content/InfraScan_rdd2022")
    ap.add_argument("--name", default="yolo11s_rdd2022_s42")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--device", default="0")
    ap.add_argument("--workers", type=int, default=2)
    a = ap.parse_args()
    root = Path(a.dataset_root)
    counts = check_dataset(root); print("dataset OK:", counts)
    data = write_yaml(root)
    run = Path(a.project) / a.name; last = run / "weights" / "last.pt"

    from ultralytics import YOLO
    kw = dict(data=str(data), epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, patience=a.patience, seed=a.seed, deterministic=True, cos_lr=True,
              workers=a.workers, device=a.device, project=a.project, name=a.name, exist_ok=True, plots=True)
    if a.time_hours:
        kw["time"] = a.time_hours
    if last.exists():
        print("RESUMING from", last)
        try:
            YOLO(str(last)).train(resume=True)
        except Exception as e:     # e.g. the run had already finished
            print("resume not possible (", e, ") - keeping existing weights")
    else:
        YOLO(a.model).train(**kw)
    best = run / "weights" / "best.pt"
    if best.exists():
        print("best.pt:", best, "\nsha256:", sha256(best), "\nrecord this hash in ml/registry/build_registry.py")


if __name__ == "__main__":
    main()
