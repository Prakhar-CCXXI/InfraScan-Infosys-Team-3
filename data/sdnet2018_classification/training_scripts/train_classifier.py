"""
InfraScan ML - binary crack classification (Positive=1 cracked, Negative=0).
Two-phase transfer learning, AMP, early stopping, checkpointing, MLflow tracking.

Usage (Kaggle GPU):
    python train_classifier.py --model resnet50 \
        --data-root /kaggle/input/datasets/nisargads192006/crack-classification \
        --splits /kaggle/working/splits/splits.csv --out-dir /kaggle/working/runs

Models: resnet50, efficientnet_b0, densenet121, mobilenet_v3_large, convnext_tiny, vit_b_16
"""
import argparse, json, random, time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score,
                             average_precision_score, precision_recall_curve)
from torch.utils.data import DataLoader, Dataset
from torchvision import models, transforms as T

IMNET_MEAN, IMNET_STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]
SIZE = 224  # images are 227x227; 224 keeps ViT happy


def seed_all(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)


class CrackDS(Dataset):
    def __init__(self, df, root, tf):
        self.p = [Path(root) / r for r in df.rel_path]
        self.y = df.y.values.astype(np.float32)
        self.tf = tf

    def __len__(self):
        return len(self.p)

    def __getitem__(self, i):
        return self.tf(Image.open(self.p[i]).convert("RGB")), self.y[i]


def transforms(size=SIZE):
    train = T.Compose([
        T.RandomResizedCrop(size, scale=(0.7, 1.0)),
        T.RandomHorizontalFlip(), T.RandomVerticalFlip(),
        T.RandomApply([T.RandomRotation((90, 90))], p=0.5),
        T.ColorJitter(brightness=0.3, contrast=0.3),  # reduces brightness/contrast shortcut
        T.ToTensor(), T.Normalize(IMNET_MEAN, IMNET_STD)])
    evalt = T.Compose([T.Resize((size, size)), T.ToTensor(), T.Normalize(IMNET_MEAN, IMNET_STD)])
    return train, evalt


def build(name):
    """Return (model, head_module) with a single-logit head."""
    if name == "resnet50":
        m = models.resnet50(weights="DEFAULT"); m.fc = nn.Linear(m.fc.in_features, 1); head = m.fc
    elif name == "efficientnet_b0":
        m = models.efficientnet_b0(weights="DEFAULT")
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, 1); head = m.classifier
    elif name == "densenet121":
        m = models.densenet121(weights="DEFAULT"); m.classifier = nn.Linear(m.classifier.in_features, 1); head = m.classifier
    elif name == "mobilenet_v3_large":
        m = models.mobilenet_v3_large(weights="DEFAULT")
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, 1); head = m.classifier
    elif name == "convnext_tiny":
        m = models.convnext_tiny(weights="DEFAULT")
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, 1); head = m.classifier
    elif name == "vit_b_16":
        m = models.vit_b_16(weights="DEFAULT"); m.heads.head = nn.Linear(m.heads.head.in_features, 1); head = m.heads
    else:
        raise ValueError(name)
    return m, head


def set_backbone_trainable(model, head, flag):
    head_ids = {id(p) for p in head.parameters()}
    for p in model.parameters():
        p.requires_grad = True if id(p) in head_ids else flag


@torch.no_grad()
def predict(model, loader, dev):
    model.eval(); ps, ys = [], []
    for x, y in loader:
        with torch.autocast(device_type=dev.type, enabled=dev.type == "cuda"):
            lo = model(x.to(dev, non_blocking=True)).squeeze(1)
        ps.append(torch.sigmoid(lo.float()).cpu().numpy()); ys.append(y.numpy())
    return np.concatenate(ps), np.concatenate(ys)


def metrics(y, p, thr=0.5):
    pred = (p >= thr).astype(int)
    return dict(accuracy=accuracy_score(y, pred), balanced_accuracy=balanced_accuracy_score(y, pred),
                precision=precision_score(y, pred, zero_division=0), recall=recall_score(y, pred),
                f1=f1_score(y, pred), auc_roc=roc_auc_score(y, p), pr_auc=average_precision_score(y, p),
                confusion_matrix=confusion_matrix(y, pred, labels=[0, 1]).tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--out-dir", default="runs")
    ap.add_argument("--epochs", type=int, default=25)
    ap.add_argument("--img-size", type=int, default=256)
    ap.add_argument("--head-epochs", type=int, default=2)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--patience", type=int, default=6)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pos-weight", type=float, default=0.0, help="0 = auto (neg/pos of train)")
    ap.add_argument("--no-mlflow", action="store_true")
    a = ap.parse_args()

    seed_all(a.seed)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out = Path(a.out_dir) / a.model; out.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(a.splits)
    assert a.model != "vit_b_16" or a.img_size == 224, "vit_b_16 needs --img-size 224"
    trt, evt = transforms(a.img_size)
    mk = lambda part, tf, sh: DataLoader(CrackDS(df[df.split == part], a.data_root, tf),
                                         batch_size=a.batch_size, shuffle=sh, num_workers=a.workers,
                                         pin_memory=True, drop_last=False)
    tr_l, va_l, te_l = mk("train", trt, True), mk("val", evt, False), mk("test", evt, False)

    model, head = build(a.model); model.to(dev)
    ytr = df[df.split == "train"].y.values
    pw = a.pos_weight if a.pos_weight > 0 else float((ytr == 0).sum() / max((ytr == 1).sum(), 1))
    crit = nn.BCEWithLogitsLoss(pos_weight=torch.tensor(pw, device=dev))
    print("pos_weight:", round(pw, 3))
    scaler = torch.cuda.amp.GradScaler(enabled=dev.type == "cuda")

    use_ml = not a.no_mlflow
    if use_ml:
        import mlflow
        mlflow.set_experiment("infrascan-crack-classification")
        mlflow.start_run(run_name=f"{a.model}-{Path(a.out_dir).name}")
        mlflow.log_params({**vars(a), "device": str(dev), "img_size": a.img_size,
                           "n_train": len(tr_l.dataset), "n_val": len(va_l.dataset), "n_test": len(te_l.dataset)})

    best_score, bad, ckpt, hist = -1, 0, out / "best.pt", []
    opt = sched = None
    for ep in range(a.epochs):
        if ep == 0:  # phase 1: head only
            set_backbone_trainable(model, head, False)
            opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=a.lr * 10, weight_decay=1e-4)
        if ep == a.head_epochs:  # phase 2: full fine-tune with cosine schedule
            set_backbone_trainable(model, head, True)
            opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=1e-4)
            sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=a.epochs - a.head_epochs)
        model.train(); tl, n, t0 = 0.0, 0, time.time()
        for x, y in tr_l:
            x, y = x.to(dev, non_blocking=True), y.to(dev, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=dev.type, enabled=dev.type == "cuda"):
                loss = crit(model(x).squeeze(1), y)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            tl += loss.item() * len(y); n += len(y)
        if sched: sched.step()
        pv, yv = predict(model, va_l, dev); vm = metrics(yv, pv)
        vloss = float(nn.functional.binary_cross_entropy(torch.tensor(pv).clamp(1e-7, 1 - 1e-7), torch.tensor(yv)))
        row = dict(epoch=ep + 1, train_loss=tl / n, val_loss=vloss, val_f1=vm["f1"], val_recall=vm["recall"],
                   val_auc=vm["auc_roc"], val_pr_auc=vm["pr_auc"], val_acc=vm["accuracy"], sec=time.time() - t0)
        hist.append(row); print(row)
        if use_ml:
            mlflow.log_metrics({k: v for k, v in row.items() if k != "epoch"}, step=ep + 1)
        if vm["pr_auc"] > best_score:  # select on PR-AUC (robust to class imbalance)
            best_score, bad = vm["pr_auc"], 0; torch.save(model.state_dict(), ckpt)
        else:
            bad += 1
            if bad >= a.patience and ep >= a.head_epochs:
                print("Early stopping"); break

    # final evaluation on held-out test with best checkpoint
    model.load_state_dict(torch.load(ckpt, map_location=dev))
    pv, yv = predict(model, va_l, dev); pt, yt = predict(model, te_l, dev)
    # thresholds are chosen on VAL only, then applied to test
    prec, rec, thr = precision_recall_curve(yv, pv)
    f1s = 2 * prec[:-1] * rec[:-1] / np.clip(prec[:-1] + rec[:-1], 1e-9, None)
    t_f1 = float(thr[int(np.argmax(f1s))])
    ok = np.where(rec[:-1] >= 0.90)[0]
    t_r90 = float(thr[ok[-1]]) if len(ok) else 0.5
    res = dict(model=a.model, best_val_pr_auc=best_score, thresholds=dict(f1=t_f1, recall90=t_r90),
               val=metrics(yv, pv), test=metrics(yt, pt),
               test_at_val_f1_threshold=metrics(yt, pt, t_f1),
               test_at_val_recall90_threshold=metrics(yt, pt, t_r90), history=hist)
    if "surface" in df.columns:
        sf = df[df.split == "test"].surface.values
        res["test_per_surface_at_val_f1_threshold"] = {s: metrics(yt[sf == s], pt[sf == s], t_f1) for s in np.unique(sf)}
    (out / "metrics.json").write_text(json.dumps(res, indent=2))
    pd.DataFrame({"y": yt, "prob": pt}).to_csv(out / "test_probs.csv", index=False)
    print(json.dumps({k: v for k, v in res.items() if k != "history"}, indent=2))
    if use_ml:
        mlflow.log_metrics({f"test_{k}": v for k, v in res["test"].items() if k != "confusion_matrix"})
        mlflow.log_artifact(str(out / "metrics.json")); mlflow.log_artifact(str(ckpt)); mlflow.end_run()


if __name__ == "__main__":
    main()
