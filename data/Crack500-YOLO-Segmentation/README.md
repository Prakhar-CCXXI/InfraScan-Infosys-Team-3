# Crack500 — YOLO11n Segmentation

## Overview

This workstream evaluates a YOLO11n segmentation model for crack segmentation on the Crack500 dataset. The final evaluation compares YOLO-only segmentation with a U-Net baseline and two hybrid approaches that combine YOLO region proposals with U-Net segmentation.

## Final test setup

- **Test images:** 1,124
- **YOLO model:** YOLO11n-seg
- **YOLO image size:** 640
- **YOLO-only confidence threshold:** 0.25
- **U-Net probability threshold:** 0.40
- **Evaluation hardware recorded in results:** NVIDIA Tesla T4

## Final test results

Metrics are percentages. The values below are taken from `final_evaluation/test_results.json`.

| Method | Dice | IoU | Precision | Recall | Mean Image Dice | Mean inference time |
|---|---:|---:|---:|---:|---:|---:|
| U-Net baseline | 74.82 | 59.76 | 71.14 | 78.89 | 70.30 | 41.78 ms/image |
| YOLO-only | 73.23 | 57.77 | 69.18 | 77.79 | 67.34 | 18.41 ms/image |
| Hybrid ROI-gated | 74.54 | 59.41 | 71.21 | 78.20 | 69.88 | 42.10 ms/image |
| Hybrid dual-threshold | 74.89 | 59.87 | 71.70 | 78.39 | 70.35 | 56.87 ms/image |

## Interpretation

- YOLO-only is the fastest method in this evaluation, with a mean inference time of about **18.41 ms/image**.
- YOLO-only mean image Dice (**67.34%**) is below the U-Net baseline (**70.30%**).
- Hybrid ROI-gated mean image Dice (**69.88%**) is also slightly below the U-Net baseline.
- Hybrid dual-threshold mean image Dice (**70.35%**) is numerically just above the U-Net baseline (**70.30%**), but paired bootstrap analysis reports **no demonstrated improvement**.
- The paired bootstrap comparison reports YOLO-only as worse than U-Net and ROI-gated as worse than U-Net for mean image Dice.

## Validation tuning (not final test results)

The validation-selected YOLO-only confidence threshold was **0.25**. Its validation metrics were:

| Dice | IoU | Precision | Recall | Mean Image Dice |
|---:|---:|---:|---:|---:|
| 80.77% | 67.74% | 79.46% | 82.12% | 74.12% |

The validation tuning results must not be mixed with the final test results above. Higher validation Dice values from hybrid tuning are validation metrics, not final held-out test performance.

## Result artifacts

The supplied final-evaluation archive includes:

- `test_results.json` — final test metrics, inference timings, and paired bootstrap comparison
- `val_yolo_only.csv` — YOLO-only validation threshold sweep
- `val_grid.csv` — hybrid validation parameter grid
- `hybrid_config.json` — selected validation configurations
- `per_image_test.csv` — per-image test results
- `visuals_test/` — example test visualizations

## Notes

The final evaluation JSON flags 37 test images for a leakage review. Its `metrics_excluding_leak_flagged` section provides a separate mean-image-Dice calculation excluding those flagged images. Refer to the JSON for the full details.

This README summarizes the evaluation archive; it does not claim that the checkpoint or dataset is included in this documentation folder.
