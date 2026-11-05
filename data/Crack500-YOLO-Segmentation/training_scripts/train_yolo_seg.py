"""
Train YOLO11n-Seg on the converted Crack500 dataset (train split only; best.pt chosen on the val split by Ultralytics).
The test split is NOT used here.

Usage (Kaggle, GPU T4, internet on for the pretrained yolo11n-seg.pt download):
  pip install ultralytics
  python train_yolo_seg.py --data /kaggle/working/yolo_crack500/crack500_yolo.yaml
"""
import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--imgsz", type=int, default=640)      # Crack500 images are ~640x360
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--device", default="0")
    ap.add_argument("--patience", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--project", default="/kaggle/working/yolo_runs")
    ap.add_argument("--name", default="yolo11n_seg_crack500")
    a = ap.parse_args()
    assert Path(a.data).is_file(), f"dataset yaml not found: {a.data}"

    from ultralytics import YOLO
    model = YOLO("yolo11n-seg.pt")
    model.train(data=a.data, epochs=a.epochs, imgsz=a.imgsz, batch=a.batch, device=a.device, patience=a.patience,
                seed=a.seed, deterministic=True, cos_lr=True, workers=2, project=a.project, name=a.name,
                exist_ok=False, plots=True)
    print("Weights:", Path(a.project) / a.name / "weights" / "best.pt")


if __name__ == "__main__":
    main()
