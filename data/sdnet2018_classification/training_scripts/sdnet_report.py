import argparse, json, re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_curve, roc_auc_score, roc_curve

# Normalized canonical names
MODELS = ["resnet50", "efficientnet_b0", "densenet121", "mobilenet_v3_large", "convnext_tiny"]
YC, PC = ["y", "y_true", "label", "target"], ["prob", "p", "probability", "pred_prob"]

def match_model_name(path_str):
    s = path_str.lower().replace("-", "_")
    if "convnext" in s:
        return "convnext_tiny"
    if "densenet" in s:
        return "densenet121"
    if "mobilenet" in s:
        return "mobilenet_v3_large"
    if "efficientnet" in s:
        return "efficientnet_b0"
    if "resnet" in s:
        return "resnet50"
    return None

def first(d, names):
    return next((n for n in names if n in d.columns), None)

def find_runs(roots, extras):
    found = {}
    def add(f, fold, model):
        if (fold, model) in found: return
        mj = f.with_name("metrics.json")
        found[(fold, model)] = dict(probs=f, metrics=json.loads(mj.read_text()) if mj.exists() else {})
    for e in extras:
        fold, model, d = e.split(":", 2)
        f = Path(d) / "test_probs.csv"
        if f.exists(): add(f, int(fold), model)
    for root in roots:
        for f in sorted(Path(root).rglob("test_probs.csv")):
            s = str(f).lower()
            fold_match = re.search(r"fold[_-]?(\d)", s)
            fold = int(fold_match.group(1)) if fold_match else 0  # Default to fold 0 if unstated
            model = match_model_name(s)
            if model:
                add(f, fold, model)
    return found

def find_split_file(splits_dir, fold):
    p = Path(splits_dir)
    # Check common locations
    candidates = [
        p / f"splits_fold{fold}.csv",
        p / "splits" / f"splits_fold{fold}.csv",
        p / "splits.csv"
    ]
    for c in candidates:
        if c.exists():
            return c
    # Fallback recursive search
    found = list(p.rglob(f"*fold{fold}*.csv"))
    if found:
        return found[0]
    found_any = list(p.rglob("splits*.csv"))
    if found_any:
        return found_any[0]
    raise FileNotFoundError(f"Could not find split CSV for fold {fold} in {splits_dir}")

def test_meta(splits_dir, fold):
    split_path = find_split_file(splits_dir, fold)
    d = pd.read_csv(split_path)
    if "split" in d.columns:
        d = d[d.split == "test"].reset_index(drop=True)
    pc = "rel_path" if "rel_path" in d.columns else "path"
    if pc in d.columns:
        parts = d[pc].astype(str).str.replace("\\", "/", regex=False).str.split("/")
        if "surface" not in d.columns: d["surface"] = parts.str[-3].str.upper().str[0]
        if "group" not in d.columns: d["group"] = d["surface"] + "_" + parts.str[-1].str.split(".").str[0].str.split("-").str[0]
    else:
        if "surface" not in d.columns: d["surface"] = "Unknown"
        if "group" not in d.columns: d["group"] = np.arange(len(d))
    d["y"] = d[first(d, ["y", "label"])].astype(int)
    return d

def at(y, p, t):
    pred = p >= t; tp = int((pred & (y == 1)).sum()); fp = int((pred & (y == 0)).sum()); fn = int((~pred & (y == 1)).sum()); tn = int((~pred & (y == 0)).sum())
    pr, rc = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    return dict(precision=pr, recall=rc, f1=2 * pr * rc / max(pr + rc, 1e-9), fpr=fp / max(fp + tn, 1), tp=tp, fp=fp, fn=fn, tn=tn)

def cluster_boot(y, probs, groups, n=1000, seed=0):
    ug, inv = np.unique(groups, return_inverse=True)
    idx_by = [np.where(inv == i)[0] for i in range(len(ug))]
    rng, out = np.random.RandomState(seed), {m: [] for m in probs}
    for _ in range(n):
        idx = np.concatenate([idx_by[i] for i in rng.randint(0, len(ug), len(ug))])
        if y[idx].min() == y[idx].max(): continue
        for m, p in probs.items(): out[m].append(average_precision_score(y[idx], p[idx]))
    return {m: np.array(v) for m, v in out.items()}

def md(df, floatfmt="{:.3f}"):
    df = df.copy()
    rows = ["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        rows.append("| " + " | ".join(floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v) for v in r) + " |")
    return "\n".join(rows)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="+", required=True)
    ap.add_argument("--splits-dir", required=True)
    ap.add_argument("--out-dir", default="sdnet_report")
    ap.add_argument("--extra", nargs="*", default=[])
    ap.add_argument("--n-boot", type=int, default=1000)
    a = ap.parse_args()
    out = Path(a.out_dir); out.mkdir(parents=True, exist_ok=True)
    runs = find_runs(a.roots, a.extra)

    inv = pd.DataFrame([dict(fold=k[0], model=k[1], probs=str(v["probs"]), has_thresholds="thresholds" in v["metrics"],
                             splits_md5=v["metrics"].get("splits_md5", "n/a")) for k, v in sorted(runs.items())])
    inv.to_csv(out / "inventory.csv", index=False)
    print("Discovered Runs Inventory:")
    print(inv.to_string(index=False))

    def load(fold, model):
        r = runs[(fold, model)]; d = pd.read_csv(r["probs"])
        return d[first(d, YC)].values.astype(int), d[first(d, PC)].values.astype(float), r["metrics"].get("thresholds", {})

    notes, report = [], ["# SDNET2018 Classification - Consolidated Results\n"]
    comp = []
    if any(k[0] == 0 for k in runs):
        meta0 = test_meta(a.splits_dir, 0); ref_y, probs, thr = meta0["y"].values, {}, {}
        for m in MODELS:
            if (0, m) not in runs: continue
            y, p, t = load(0, m)
            if len(y) != len(ref_y) or not np.array_equal(y, ref_y):
                notes.append(f"EXCLUDED {m}: test labels do not match split reference rows.")
                continue
            probs[m], thr[m] = p, t
        y0 = ref_y; boot = cluster_boot(y0, probs, meta0["group"].values, a.n_boot)
        best = max(probs, key=lambda m: average_precision_score(y0, probs[m]))
        for m, p in probs.items():
            row = dict(model=m, roc_auc=roc_auc_score(y0, p), pr_auc=average_precision_score(y0, p))
            lo, hi = np.percentile(boot[m], [2.5, 97.5]); row["pr_auc_ci95"] = f"[{lo:.3f}, {hi:.3f}]"
            if m != best:
                d = boot[best] - boot[m]; l2, h2 = np.percentile(d, [2.5, 97.5]); row[f"pr_auc_diff_vs_{best}"] = f"{-d.mean():+.3f} [{-h2:+.3f}, {-l2:+.3f}]"
            else:
                row[f"pr_auc_diff_vs_{best}"] = "(reference)"
            for name, t in [("thr0.5", 0.5), ("val_f1", thr[m].get("f1")), ("val_recall90", thr[m].get("recall90"))]:
                if t is None or isinstance(t, str): continue
                r = at(y0, p, t); row.update({f"{name}_prec": r["precision"], f"{name}_rec": r["recall"], f"{name}_f1": r["f1"]})
                if name == "val_recall90": row["val_recall90_fpr"] = r["fpr"]
            comp.append(row)
        cdf = pd.DataFrame(comp).sort_values("pr_auc", ascending=False); cdf.to_csv(out / "fold0_model_comparison.csv", index=False)
        for fn, curve, xl, yl in (("pr_curves.png", precision_recall_curve, "recall", "precision"), ("roc_curves.png", roc_curve, "FPR", "TPR")):
            plt.figure(figsize=(6, 5))
            for m, p in probs.items():
                a1, a2, _ = curve(y0, p); plt.plot(*((a2, a1) if curve is precision_recall_curve else (a1, a2)), label=m)
            plt.xlabel(xl); plt.ylabel(yl); plt.legend(); plt.grid(alpha=.3); plt.title(f"Fold 0 Test: {fn[:2].upper()} Curves"); plt.tight_layout(); plt.savefig(out / fn, dpi=120); plt.close()
        t90 = thr[best].get("recall90", 0.5); t90 = 0.5 if isinstance(t90, str) else t90
        cm = confusion_matrix(y0, probs[best] >= t90, labels=[0, 1]); plt.figure(figsize=(3.8, 3.4)); plt.imshow(cm, cmap="Blues")
        for (i, j), v in np.ndenumerate(cm): plt.text(j, i, str(v), ha="center", va="center")
        plt.xticks([0, 1], ["pred 0", "pred 1"]); plt.yticks([0, 1], ["true 0", "true 1"]); plt.title(f"{best} @ val-recall90 thr {t90:.3f}"); plt.tight_layout(); plt.savefig(out / "confusion_selected.png", dpi=120); plt.close()
        report += ["## Fold 0: Model Comparison (Identical Test Set Verified)\n", md(cdf), ""]
        sel = best
    else:
        sel = "convnext_tiny"; notes.append("No fold-0 outputs found.")

    if notes: report += ["\n## Notes from this run\n"] + [f"- {n}" for n in notes]
    (out / "sdnet_report.md").write_text("\n".join(report))
    print("\nReport generated successfully at:", out / "sdnet_report.md")

if __name__ == "__main__":
    main()
