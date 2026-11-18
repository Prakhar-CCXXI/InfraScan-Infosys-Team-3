"""
Make Grad-CAM panels (original | CAM overlay) for a few images.
  python ml/explain/gradcam_cli.py --task classifier --checkpoint <ConvNeXt best.pt> --images a.jpg b.jpg --out-dir cam_out [--img-size 256] [--plus]
  python ml/explain/gradcam_cli.py --task segmentation --checkpoint <U-Net best.pt> --images a.jpg --out-dir cam_out
"""
import argparse, sys
from pathlib import Path
import cv2, numpy as np, torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gradcam import explain_classifier, explain_segmentation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", choices=["classifier", "segmentation"], required=True)
    ap.add_argument("--checkpoint", required=True); ap.add_argument("--images", nargs="+", required=True); ap.add_argument("--out-dir", default="cam_out")
    ap.add_argument("--img-size", type=int, default=256); ap.add_argument("--thr", type=float, default=0.4); ap.add_argument("--plus", action="store_true")
    a = ap.parse_args()
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if a.task == "classifier":
        from torchvision import models
        model = models.convnext_tiny(weights=None); model.classifier[-1] = torch.nn.Linear(model.classifier[-1].in_features, 1)   # same head as train_classifier.py
    else:
        import segmentation_models_pytorch as smp
        model = smp.Unet(encoder_name="resnet34", encoder_weights=None, in_channels=3, classes=1)
    print(model.load_state_dict(torch.load(a.checkpoint, map_location=dev)))
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    for p in a.images:
        bgr = cv2.imread(p); rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        if a.task == "classifier":
            prob, cam, ov = explain_classifier(model, rgb, dev, a.img_size, plus=a.plus); title = f"crack probability {prob:.2f}"
        else:
            cam, ov = explain_segmentation(model, rgb, dev, a.thr, plus=a.plus); title = "CAM for the predicted mask"
        panel = np.hstack([bgr, ov]); cv2.putText(panel, title, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(str(out / f"{Path(p).stem}_cam.jpg"), panel); print("wrote", out / f"{Path(p).stem}_cam.jpg", "|", title)


if __name__ == "__main__":
    main()
