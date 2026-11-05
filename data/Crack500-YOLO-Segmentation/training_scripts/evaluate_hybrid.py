"""
Evaluate U-Net baseline vs YOLO-only vs hybrid on the same Crack500 split with the SAME metric code.

  --stage tune : VALIDATION only. Caches U-Net probabilities + YOLO detections, checks that the U-Net baseline
                 reproduces its recorded validation Dice, grid-searches fusion parameters, writes hybrid_config.json.
  --stage test : ONE-SHOT test evaluation with the frozen config (refuses to run twice unless --force).
                 Reports Dice/IoU/precision/recall/mean-image-Dice, inference time, a paired bootstrap verdict,
                 and a sensitivity analysis excluding images flagged by the leakage audit.

Usage:
  python evaluate_hybrid.py --stage tune --manifest M --yolo-ckpt Y --unet-ckpt U --unet-metrics UM --out-dir D
  python evaluate_hybrid.py --stage test --manifest M --yolo-ckpt Y --unet-ckpt U --unet-metrics UM --out-dir D
"""
import argparse, itertools, json, sys, time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hybrid_pipeline import HybridConfig, HybridCrackPipeline, fuse, make_region, render_panel  # noqa: E402

CONFS = [0.10, 0.25, 0.40]
GATES = ["box", "mask"]
MARGINS = [8, 24]
T_IN = [0.3, 0.4, 0.5, 0.6]
T_OUT = [None, 0.8, 0.9]
YOLO_ONLY_CONFS = [0.05, 0.10, 0.25, 0.40, 0.50]


def read_pair(r):
    bgr = cv2.imread(r.img_path)
    gt = cv2.imread(r.mask_path, cv2.IMREAD_UNCHANGED)
    gt = gt[..., 0] if gt.ndim == 3 else gt
    return bgr, (gt > 0).astype(np.uint8)


class Acc:
    """Global pixel counts (same definition as train_seg.py) + per-image Dice (NaN when the image has no GT crack)."""
    def __init__(self):
        self.tp = self.fp = self.fn = 0
        self.img = []

    def add(self, pred, gt):
        p, g = pred > 0, gt > 0
        tp, fp, fn = int((p & g).sum()), int((p & ~g).sum()), int((~p & g).sum())
        self.tp += tp; self.fp += fp; self.fn += fn
        self.img.append(2 * tp / max(2 * tp + fp + fn, 1) if g.any() else np.nan)

    def summary(self, mask=None):
        d = np.array(self.img)
        d = d if mask is None else d[mask]
        tp, fp, fn = self.tp, self.fp, self.fn
        return dict(dice=2 * tp / max(2 * tp + fp + fn, 1), iou=tp / max(tp + fp + fn, 1),
                    precision=tp / max(tp + fp, 1), recall=tp / max(tp + fn, 1),
                    mean_image_dice=float(np.nanmean(d)) if np.isfinite(d).any() else 0.0)


def union_masks(masks, confs, conf, shape):
    sel = confs >= conf
    return np.max(masks[sel], 0) if sel.any() else np.zeros(shape, np.uint8)


def subset_metrics(dice_img, flag_mask):
    d = np.array(dice_img)
    return float(np.nanmean(d[flag_mask])) if np.isfinite(d[flag_mask]).any() else None


def load_df(a):
    df = pd.read_csv(a.manifest)
    if a.leak_flags and Path(a.leak_flags).exists():
        fl = pd.read_csv(a.leak_flags)[["split", "stem", "leak_flag"]]
        df = df.merge(fl, on=["split", "stem"], how="left")
        df["leak_flag"] = df["leak_flag"].fillna(False).astype(bool)
    else:
        df["leak_flag"] = False
    return df


# ------------------------------------------------ tune (validation only) ------------------------------------------------
def stage_tune(a, pipe, df):
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    val = df[df.split == "val"].reset_index(drop=True)
    cache = []
    for i, r in val.iterrows():
        bgr, gt = read_pair(r)
        prob = pipe.unet_prob(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        b, c, m = pipe.yolo_detect(bgr, conf=min(YOLO_ONLY_CONFS + CONFS))
        cache.append((gt, prob, b, c, m))
        if i % 50 == 0: print(f"cached {i}/{len(val)}", flush=True)

    base = Acc()
    for gt, prob, *_ in cache: base.add(prob >= a.unet_thr, gt)
    bs = base.summary()
    ref = json.loads(Path(a.unet_metrics).read_text())["val_sweep"][str(a.unet_thr)]["dice"]
    print(f"U-Net baseline val Dice {bs['dice']:.4f} vs recorded {ref:.4f}"
          + ("  OK" if abs(bs["dice"] - ref) < 0.003 else "  !! MISMATCH: check checkpoint/preprocessing"))

    yolo_rows = []
    for conf in YOLO_ONLY_CONFS:
        acc = Acc()
        for gt, prob, b, c, m in cache: acc.add(union_masks(m, c, conf, gt.shape), gt)
        yolo_rows.append(dict(yolo_conf=conf, **acc.summary()))
    best_y = max(yolo_rows, key=lambda r: r["dice"])

    rows = []
    for conf, gate, margin in itertools.product(CONFS, GATES, MARGINS):
        cfg0 = HybridConfig(yolo_conf=conf, gate=gate, margin=margin)
        regions = []
        for gt, prob, b, c, m in cache:
            sel = c >= conf
            regions.append(make_region(cfg0, b[sel], m[sel], gt.shape))
        for t_in, t_out in itertools.product(T_IN, T_OUT):
            acc = Acc()
            for (gt, prob, *_), reg in zip(cache, regions): acc.add(fuse(prob, reg, t_in, t_out), gt)
            rows.append(dict(yolo_conf=conf, gate=gate, margin=margin, t_in=t_in, t_out=t_out, **acc.summary()))
        print("grid", conf, gate, margin, flush=True)
    grid = pd.DataFrame(rows).sort_values("dice", ascending=False)
    grid.to_csv(out / "val_grid.csv", index=False)

    def cfg_of(row):
        return HybridConfig(yolo_conf=float(row.yolo_conf), gate=row.gate, margin=int(row.margin), t_in=float(row.t_in),
                            t_out=None if pd.isna(row.t_out) else float(row.t_out))
    best_roi = grid[grid.t_out.isna()].iloc[0]
    best_dual = grid[grid.t_out.notna()].iloc[0]
    cfgs = dict(unet_thr=a.unet_thr, yolo_only=dict(yolo_conf=best_y["yolo_conf"], val=best_y),
                roi_gated=dict(config=cfg_of(best_roi).__dict__, val_gated_approx=best_roi.drop(["yolo_conf", "gate", "margin", "t_in", "t_out"]).to_dict()),
                dual_threshold=dict(config=cfg_of(best_dual).__dict__, val_gated_approx=best_dual.drop(["yolo_conf", "gate", "margin", "t_in", "t_out"]).to_dict()),
                unet_baseline_val=bs)

    # confirm with the REAL pipeline (true ROI-crop inference for roi_gated) on validation
    for key in ("roi_gated", "dual_threshold"):
        cfg = HybridConfig(**cfgs[key]["config"]); acc = Acc(); tms = []
        for _, r in val.iterrows():
            bgr, gt = read_pair(r)
            res = pipe.predict(bgr, cfg, measure=False)
            acc.add(res["hybrid_mask"], gt); tms.append(res["timing_ms"]["total_ms"])
        cfgs[key]["val_true_pipeline"] = dict(**acc.summary(), mean_ms=float(np.mean(tms[3:])))
        print(key, "val approx Dice", round(cfgs[key]["val_gated_approx"]["dice"], 4),
              "| true pipeline Dice", round(cfgs[key]["val_true_pipeline"]["dice"], 4))
    (out / "hybrid_config.json").write_text(json.dumps(cfgs, indent=2, default=float))
    pd.DataFrame(yolo_rows).to_csv(out / "val_yolo_only.csv", index=False)
    print(json.dumps({k: cfgs[k] for k in ("unet_baseline_val", "yolo_only")}, indent=2, default=float))
    print("Best VAL configs written to", out / "hybrid_config.json", "(test not touched)")


# ------------------------------------------------ test (one shot) ------------------------------------------------
def bootstrap_verdict(base, hyb, n=2000, seed=0):
    b, h = np.array(base), np.array(hyb)
    ok = np.isfinite(b) & np.isfinite(h)
    d = (h - b)[ok]
    rng = np.random.RandomState(seed)
    means = np.array([d[rng.randint(0, len(d), len(d))].mean() for _ in range(n)])
    lo, hi = np.percentile(means, [2.5, 97.5])
    verdict = ("IMPROVEMENT demonstrated" if lo > 0 else "WORSE than baseline" if hi < 0 else "NO demonstrated improvement")
    return dict(mean_image_dice_diff=float(d.mean()), ci95=[float(lo), float(hi)], n_images=int(ok.sum()), verdict=verdict)


def stage_test(a, pipe, df):
    out = Path(a.out_dir)
    res_path = out / "test_results.json"
    if res_path.exists() and not a.force:
        raise SystemExit(f"{res_path} exists: the test set was already evaluated. Use --force only to re-run deliberately.")
    cfgs = json.loads((out / "hybrid_config.json").read_text())
    cfg_roi, cfg_dual = HybridConfig(**cfgs["roi_gated"]["config"]), HybridConfig(**cfgs["dual_threshold"]["config"])
    yconf = cfgs["yolo_only"]["yolo_conf"]
    test = df[df.split == "test"].reset_index(drop=True)
    names = ["unet", "yolo_only", "hybrid_roi_gated", "hybrid_dual_threshold"]
    acc = {k: Acc() for k in names}
    ms = {k: [] for k in names}
    n_boxes, no_det = [], []
    for i, r in test.iterrows():
        bgr, gt = read_pair(r)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pipe.sync(); t0 = time.perf_counter()
        pm = pipe.unet_prob(rgb) >= cfgs["unet_thr"]; pipe.sync(); ms["unet"].append(1000 * (time.perf_counter() - t0))
        t0 = time.perf_counter()
        b, c, m = pipe.yolo_detect(bgr, yconf); ym = union_masks(m, c, yconf, gt.shape)
        pipe.sync(); ms["yolo_only"].append(1000 * (time.perf_counter() - t0))
        r1 = pipe.predict(bgr, cfg_roi, measure=False); r2 = pipe.predict(bgr, cfg_dual, measure=False)
        ms["hybrid_roi_gated"].append(r1["timing_ms"]["total_ms"]); ms["hybrid_dual_threshold"].append(r2["timing_ms"]["total_ms"])
        for k, p in zip(names, [pm, ym, r1["hybrid_mask"], r2["hybrid_mask"]]): acc[k].add(p, gt)
        n_boxes.append(len(r1["boxes"])); no_det.append(not r1["yolo_detected"])
        if i % 100 == 0: print(f"test {i}/{len(test)}", flush=True)

    leak = test.leak_flag.values
    res = dict(n_test=len(test), unet_thr=cfgs["unet_thr"], gpu=(pipe.torch.cuda.get_device_name(0) if pipe.device.type == "cuda" else "cpu"),
               configs=dict(yolo_conf=yconf, roi_gated=cfgs["roi_gated"]["config"], dual_threshold=cfgs["dual_threshold"]["config"]),
               metrics={k: acc[k].summary() for k in names},
               metrics_excluding_leak_flagged={k: acc[k].summary(mask=~leak) for k in names} if leak.any() else None,
               n_leak_flagged_test_images=int(leak.sum()),
               inference_ms={k: dict(mean=float(np.mean(v[3:])), median=float(np.median(v[3:])), p95=float(np.percentile(v[3:], 95))) for k, v in ms.items()},
               yolo_no_detection_images=int(sum(no_det)),
               paired_bootstrap_vs_unet={k: bootstrap_verdict(acc["unet"].img, acc[k].img) for k in names[1:]},
               note="Hybrid timing = YOLO + U-Net + fusion (batch 1, includes pre/post-processing, excludes image decoding and geometry). "
                    "Two hybrid variants were pre-declared from validation; interpret p-values with that in mind.")
    res_path.write_text(json.dumps(res, indent=2, default=float))
    pd.DataFrame(dict(stem=test.stem, leak_flag=leak, n_boxes=n_boxes, **{f"dice_{k}": acc[k].img for k in names})).to_csv(out / "per_image_test.csv", index=False)
    print(json.dumps({k: res[k] for k in ("metrics", "inference_ms", "paired_bootstrap_vs_unet")}, indent=2, default=float))

    # visual outputs (do not influence any decision)
    vis = out / "visuals_test"; vis.mkdir(exist_ok=True)
    rng = np.random.RandomState(0)
    ids = list(rng.choice(len(test), min(16, len(test)), replace=False)) + [i for i, f in enumerate(no_det) if f][:6]
    d_unet, d_h = np.array(acc["unet"].img), np.array(acc["hybrid_roi_gated"].img)
    diff = np.nan_to_num(d_h - d_unet)
    ids += list(np.argsort(diff)[:3]) + list(np.argsort(-diff)[:3])
    for i in dict.fromkeys(int(x) for x in ids):
        r = test.iloc[i]; bgr, gt = read_pair(r)
        res_i = pipe.predict(bgr, cfg_roi, measure=False)
        um = pipe.unet_prob(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)) >= cfgs["unet_thr"]
        cv2.imwrite(str(vis / f"{r.stem}.jpg"), render_panel(bgr, res_i, gt=gt, unet_mask=um.astype(np.uint8)))
    print("visuals:", vis)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["tune", "test"], required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--yolo-ckpt", required=True)
    ap.add_argument("--unet-ckpt", required=True)
    ap.add_argument("--unet-metrics", required=True, help="metrics.json of the U-Net run (for val reproduction check)")
    ap.add_argument("--leak-flags", default=None, help="split_leak_flags.csv from prepare_yolo_dataset.py")
    ap.add_argument("--unet-thr", type=float, default=0.4)
    ap.add_argument("--out-dir", default="/kaggle/working/hybrid_eval")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    pipe = HybridCrackPipeline(a.yolo_ckpt, a.unet_ckpt)
    df = load_df(a)
    stage_tune(a, pipe, df) if a.stage == "tune" else stage_test(a, pipe, df)


if __name__ == "__main__":
    main()
