"""
Builds ml/registry/model_registry.json and docs/model_cards/*.md from ONE source of truth (the MODELS list below).
Evidence levels:  VERIFIED_FROM_FILES | REPORTED_IN_CHAT_JSON | REPORTED_NOT_VERIFIED
Edit a value here, re-run, and the registry and cards stay consistent.   Usage: python ml/registry/build_registry.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NV = "NEEDS VERIFICATION"
DISCLAIMER = "Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment."

MODELS = [
 dict(id="crack500-unet-resnet34-v1.0", title="Crack500 U-Net (ResNet34) - crack segmentation", status="FROZEN v1.0 (model of record for segmentation)",
  evidence="VERIFIED_FROM_FILES (metrics.json, test_metrics.json, config.json, checkpoint SHA256; test Dice re-derived independently by the hybrid evaluation)",
  task="Pixel-level binary crack segmentation", dataset="Crack500 (official split: train 1,896 / val 348 / test 1,124 image-mask pairs)",
  architecture="segmentation_models_pytorch Unet, ResNet34 encoder (ImageNet-initialised), 1 output channel",
  checkpoint=dict(path="/kaggle/working/seg_runs/unet_resnet34_s42/best.pt", sha256="684484b1f408b3e3af18115613f9713a8ec8d62b5f697976a877a2614abc2163", size_bytes=97903743),
  training=dict(crop=352, epochs=40, batch_size=8, lr=3e-4, optimizer="AdamW (wd 1e-4), cosine schedule", loss="BCE + Dice", precision="AMP", early_stopping_patience=8, seed=42,
                manifest_md5="3c43cfc22afcf8a1954c14b0b3c1c58f", script="ml/segmentation/train_seg.py"),
  operating_point=dict(threshold=0.4, chosen_on="validation only"),
  results=dict(validation_at_0_4=dict(dice=0.8206, iou=0.6958, precision=0.8065, recall=0.8352, mean_image_dice=0.7625, boundary_f1_2_4_8px=[0.4621, 0.6703, 0.8518]),
               test_at_0_4=dict(dice=0.7482, iou=0.5976, precision=0.7114, recall=0.7889, mean_image_dice=0.7030, boundary_f1_2_4_8px=[0.3923, 0.5884, 0.7936]),
               architecture_comparison_val_dice=dict(unet_resnet34=0.8206, deeplabv3plus_resnet34=0.8162, unetplusplus_resnet34=0.8126, unet_scse=0.8098),
               seeds_val_dice=dict(seed1=0.8109, seed2=0.8158, seed42=0.8206, mean=0.8158, sd=0.0048)),
  limitations=["Test Dice is about 7 points below validation Dice; report both.", "Architecture differences (<=0.8 pt) are within seed noise (SD 0.48 pt); U-Net was chosen for simplicity, not demonstrated superiority.",
               "Seed 42 was the best of 3 seeds, so its validation score is slightly optimistic; the test score is unaffected.", "Crack500 is pavement imagery; behaviour on concrete decks/walls is untested.",
               "Annotations are thick and coarse: boundary F1 is 39% at 2 px tolerance, 79% at 8 px.", "Official split has 80 images in source photos shared across splits (37 in test); sensitivity analysis shows no material effect on mean image Dice.",
               "Measurements derived from masks are in pixels only (no calibration)."],
  not_for=["Structural safety decisions", "Physical (mm) measurements without a calibrated scale"], pending=["Confirm best.pt hash on the deployment copy"]),

 dict(id="crack500-yolo11n-seg-v0.1", title="Crack500 YOLO11n-Seg - crack localisation (experiment)", status="EXPERIMENTAL v0.1 (not the segmentation model of record)",
  evidence="PARTLY VERIFIED: label conversion report and validation/test metrics from files; weights hash, training args and detection mAP not provided",
  task="Crack localisation (boxes, confidence) and coarse instance masks", dataset="Crack500, labels converted from masks to YOLO polygons; official split preserved",
  architecture="Ultralytics YOLO11n-Seg (pretrained yolo11n-seg.pt), 1 class",
  checkpoint=dict(path=NV, sha256=NV), training=dict(script="ml/hybrid/train_yolo_seg.py", defaults="100 epochs, imgsz 640, batch 16, patience 20, seed 42, cosine LR (check args.yaml: " + NV + ")",
        label_conversion=dict(polygons=7258, dropped_tiny_components=1484, polygon_vs_mask_iou_mean=0.9748, polygon_vs_mask_iou_p05=0.9379, share_below_0_8=0.0077)),
  operating_point=dict(yolo_conf=0.25, chosen_on="validation only"),
  results=dict(validation=dict(dice=0.8077, iou=0.6774, precision=0.7946, recall=0.8212, mean_image_dice=0.7412),
               test=dict(dice=0.7323, iou=0.5777, precision=0.6918, recall=0.7779, mean_image_dice=0.6734, images_with_no_detection=13, mean_inference_ms_T4=18.4),
               vs_unet_test_paired_bootstrap=dict(mean_image_dice_diff=-0.0296, ci95=[-0.0371, -0.0221], verdict="WORSE than U-Net"),
               detection_map="NOT YET MEASURED on Crack500 (run Ultralytics val once on the frozen best.pt and record box/mask mAP50, mAP50-95)"),
  limitations=["Masks are coarse (prototype masks at 1/4 input resolution); thin cracks lose detail.", "Mask-to-polygon conversion fills holes and drops components under 6 px.", "Do not compare with the Crack-seg demo model: different dataset."],
  not_for=["Primary segmentation (use the U-Net)"], pending=["best.pt SHA256 and args.yaml", "Box/mask mAP on the test split (one run, frozen weights)"]),

 dict(id="crack500-hybrid-v0.1", title="Hybrid pipeline: YOLO11n-Seg gating + U-Net masks", status="EXPERIMENTAL v0.1 (optional component)",
  evidence="VERIFIED_FROM_FILES (hybrid_config.json, val_grid.csv, test_results.json); one-shot test evaluation",
  task="Boxes + confidence from YOLO, pixel masks from U-Net, fused by a gating rule (not a plain OR)", dataset="Crack500 official split",
  architecture="HybridCrackPipeline (ml/hybrid/hybrid_pipeline.py); fusion: U-Net prob >= t_in inside YOLO region, >= t_out outside (None = nothing outside)",
  checkpoint=dict(path="U-Net v1.0 + YOLO v0.1 weights", sha256="see component entries"),
  training=dict(selection="144-config grid on validation only; two variants declared before the test run", configs=dict(
        roi_gated=dict(yolo_conf=0.1, gate="mask", margin=8, t_in=0.4, t_out=None), dual_threshold=dict(yolo_conf=0.1, gate="mask", margin=8, t_in=0.4, t_out=0.9))),
  operating_point=dict(unet_thr=0.4),
  results=dict(test=dict(unet_baseline=dict(dice=0.7482, iou=0.5976, precision=0.7114, recall=0.7889, mean_image_dice=0.7030, ms=41.8),
                         yolo_only=dict(dice=0.7323, iou=0.5777, precision=0.6918, recall=0.7779, mean_image_dice=0.6734, ms=18.4),
                         hybrid_roi_gated=dict(dice=0.7454, iou=0.5941, precision=0.7121, recall=0.7820, mean_image_dice=0.6988, ms=42.1),
                         hybrid_dual_threshold=dict(dice=0.7489, iou=0.5987, precision=0.7170, recall=0.7839, mean_image_dice=0.7035, ms=56.9)),
               paired_bootstrap_vs_unet=dict(hybrid_roi_gated="WORSE (diff -0.0042, CI [-0.0076, -0.0008])", hybrid_dual_threshold="NO demonstrated improvement (diff +0.0005, CI [-0.0005, +0.0015])")),
  limitations=["No segmentation accuracy gain over the U-Net alone; the value is boxes + detection confidence.", "ROI-crop mode gave no speed gain on 640x360 images (ROIs cover most of the image); gains on large images are untested.",
               "Pooled metrics excluding leak-flagged images were reported incorrectly by the first evaluator version (bug fixed; only the mean-image-Dice sensitivity is valid: U-Net 0.7021 vs dual 0.7025)."],
  not_for=["Claims of improved segmentation accuracy"], pending=[]),

 dict(id="sdnet2018-convnext-tiny-v1.0", title="SDNET2018 ConvNeXt-Tiny - crack / no-crack patch classification", status="v1.0 selected (statistically tied with DenseNet121)",
  evidence="Fold-0 comparison VERIFIED_FROM_FILES (sdnet_report.md, inventory.csv); thresholds and fold-0 test counts from a pasted metrics.json; five-fold summary REPORTED_NOT_VERIFIED",
  task="Binary classification of 256x256 concrete patches (decks, pavements, walls)", dataset="SDNET2018, 56,092 images; photo-grouped 5-fold splits (group = surface + filename prefix); fold 0 used for model comparison",
  architecture="torchvision ConvNeXt-Tiny, ImageNet-initialised, single logit, two-phase fine-tuning, weighted BCE",
  checkpoint=dict(path="/kaggle/working/convnext_tiny_backup/best.pt (fold 0)", sha256=NV), training=dict(script="ml/training/train_classifier.py", image_size=NV, selection="best validation PR-AUC"),
  operating_point=dict(default="validation recall-90% threshold (0.5058, fold 0)", alternative="validation best-F1 threshold (0.8991, fold 0)", chosen_on="validation only"),
  results=dict(fold0_test=dict(roc_auc=0.953, pr_auc=0.886, pr_auc_ci95_photo_bootstrap=[0.847, 0.917]),
               fold0_test_at_recall90_thr=dict(precision=0.576, recall=0.897, f1=0.701, false_alarm_rate=0.130),
               fold0_test_at_f1_thr=dict(precision=0.860, recall=0.772, f1=0.813),
               fold0_model_comparison_pr_auc=dict(convnext_tiny=0.886, densenet121=0.884, efficientnet_b0=0.877, mobilenet_v3_large=0.867, note="ConvNeXt vs DenseNet diff -0.001 [-0.015,+0.010]: tie; MobileNetV3 lower by 0.018 [-0.030,-0.009]"),
               five_fold_reported=dict(pr_auc="85.04 +/- 4.53 pp", roc_auc="93.92 +/- 1.98 pp", precision="45.63 +/- 10.48 pp", recall="90.17 +/- 2.32 pp", f1="59.94 +/- 9.35 pp",
                                      caveat="fold configurations were not controlled; files not re-verified"),
               five_fold_false_alarm_rate_reported=dict(deck=0.272, pavement=0.113, wall=0.302)),
  limitations=["Fold 0 scores higher than the reported five-fold mean (PR-AUC 88.6 vs 85.0); quote both.", "At 90% recall, about 42% of alerts are false (precision 57.6% on fold 0, ~46% reported across folds).",
               "Blind audit (one fold, one non-expert reviewer): of 60 most-confident false positives, 28 looked like real cracks and 22 ambiguous; of 40 lowest-scoring 'cracked' images, 30 showed no crack. Tail samples only, not a dataset noise rate.",
               "Does not transfer from the Concrete Crack dataset; trained on SDNET2018 only.", "ResNet50 was excluded from the consolidated comparison: no verifiable output on the same test set (an earlier run used a different split, PR-AUC 0.805 not comparable)."],
  not_for=["Structural safety decisions", "Crack width/length measurement"], pending=["Checkpoint hash and image size", "Fold 1-4 outputs if the five-fold table is to be re-verified"]),

 dict(id="concrete-crack-resnet50-baseline-v0.1", title="Concrete Crack Images ResNet50 - binary baseline", status="BASELINE v0.1 (not for deployment)",
  evidence="REPORTED_IN_CHAT_JSON; split report VERIFIED_FROM_FILES (uploaded zips)",
  task="Binary crack/no-crack classification of 227x227 patches", dataset="Concrete Crack Images for Classification: 40,000 -> 38,402 after exact-duplicate removal; grouped split train 26,892 / val 5,773 / test 5,737",
  architecture="torchvision ResNet50, ImageNet-initialised", checkpoint=dict(path=NV, sha256=NV), training=dict(script="ml/training/train_classifier.py"),
  operating_point=dict(threshold=0.5),
  results=dict(test=dict(accuracy=0.99895, precision=0.99899, recall=0.99899, f1=0.99899, auc_roc=0.99999, confusion_matrix=[[2763, 3], [3, 2968]]),
               external_sdnet2018=dict(accuracy=0.833, precision=0.432, recall=0.328, f1=0.373, auc_roc=0.707, pr_auc=0.319)),
  limitations=["In-domain score is saturated (a 3-feature logistic regression reaches 96.7%); it says little about real performance.", "Fails on SDNET2018 (ROC-AUC 0.71): learned texture/contrast shortcuts."],
  not_for=["Any deployment", "Evidence of real-world accuracy"], pending=["Checkpoint path/hash if it is kept"]),

 dict(id="crack-seg-yolo11n-demo-v0", title="Crack-seg YOLO11n-Seg - existing FastAPI demo model", status="DEMO v0 (preserved unchanged)",
  evidence="App code VERIFIED_FROM_FILES (app.py, scripts, README); training metrics REPORTED_NOT_VERIFIED (no results.csv provided)",
  task="Demo crack detection + masks inside the FastAPI intake app", dataset="Crack-seg dataset (train 3,717 / val 112 / test 200); NOT Crack500",
  architecture="Ultralytics YOLO11n-Seg, 1 class ('crack')", checkpoint=dict(path="runs/infrascan_demo/crack_seg_baseline/weights/best.pt", sha256=NV),
  training=dict(epochs=3, imgsz=320, batch=2, device="cpu", script="scripts/train_demo.py"), operating_point=dict(confidence=0.25),
  results=dict(reported=dict(box_map50=0.666, box_map50_95=0.365, mask_map50=0.540, mask_map50_95=0.175)),
  limitations=["3 epochs on CPU at 320 px: a pipeline demonstration, not a quality benchmark.", "Not comparable with Crack500 models (different data).",
               "Demo quality checks: brightness<45, Laplacian variance<60; the blur rule mislabels smooth concrete (uncracked concrete patches average ~32) and depends on resolution.",
               "Stored 'original' is re-encoded to JPEG; README text still says ai_prediction 'not_run'; page text mentions normalisation that the code does not perform."],
  not_for=["Production use"], pending=["results.csv, args.yaml, weights hash"]),
]


def fmt(v, ind=0):
    pad = "  " * ind
    if isinstance(v, dict):
        return "\n".join(f"{pad}- **{k}**: " + (fmt(x, ind + 1) if isinstance(x, dict) else str(x)).lstrip() if not isinstance(x, dict) else f"{pad}- **{k}**:\n{fmt(x, ind + 1)}" for k, x in v.items())
    return f"{pad}{v}"


def card(m):
    s = [f"# {m['title']}", f"**ID:** `{m['id']}`  \n**Status:** {m['status']}  \n**Evidence:** {m['evidence']}", f"\n> {DISCLAIMER}\n",
         f"## Task\n{m['task']}", f"## Data\n{m['dataset']}", f"## Architecture\n{m['architecture']}",
         "## Checkpoint\n" + fmt(m["checkpoint"]), "## Training / configuration\n" + fmt(m["training"]),
         "## Operating point\n" + fmt(m["operating_point"]), "## Results\n" + fmt(m["results"]),
         "## Known limitations\n" + "\n".join(f"- {x}" for x in m["limitations"]),
         "## Not for\n" + "\n".join(f"- {x}" for x in m["not_for"])]
    if m["pending"]:
        s.append("## Pending verification\n" + "\n".join(f"- {x}" for x in m["pending"]))
    return "\n\n".join(s) + "\n"


def main():
    reg = ROOT / "ml" / "registry"; cards = ROOT / "docs" / "model_cards"
    reg.mkdir(parents=True, exist_ok=True); cards.mkdir(parents=True, exist_ok=True)
    (reg / "model_registry.json").write_text(json.dumps(dict(schema="infrascan-model-registry-1", disclaimer=DISCLAIMER, models=MODELS), indent=2))
    for m in MODELS:
        (cards / f"{m['id']}.md").write_text(card(m))
    print("registry:", reg / "model_registry.json", "| cards:", len(MODELS))


if __name__ == "__main__":
    main()
