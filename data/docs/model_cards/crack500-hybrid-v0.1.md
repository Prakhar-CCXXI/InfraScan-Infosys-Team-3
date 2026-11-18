# Hybrid pipeline: YOLO11n-Seg gating + U-Net masks

**ID:** `crack500-hybrid-v0.1`  
**Status:** EXPERIMENTAL v0.1 (optional component)  
**Evidence:** VERIFIED_FROM_FILES (hybrid_config.json, val_grid.csv, test_results.json); one-shot test evaluation


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Boxes + confidence from YOLO, pixel masks from U-Net, fused by a gating rule (not a plain OR)

## Data
Crack500 official split

## Architecture
HybridCrackPipeline (ml/hybrid/hybrid_pipeline.py); fusion: U-Net prob >= t_in inside YOLO region, >= t_out outside (None = nothing outside)

## Checkpoint
- **path**: U-Net v1.0 + YOLO v0.1 weights
- **sha256**: see component entries

## Training / configuration
- **selection**: 144-config grid on validation only; two variants declared before the test run
- **configs**:
  - **roi_gated**:
    - **yolo_conf**: 0.1
    - **gate**: mask
    - **margin**: 8
    - **t_in**: 0.4
    - **t_out**: None
  - **dual_threshold**:
    - **yolo_conf**: 0.1
    - **gate**: mask
    - **margin**: 8
    - **t_in**: 0.4
    - **t_out**: 0.9

## Operating point
- **unet_thr**: 0.4

## Results
- **test**:
  - **unet_baseline**:
    - **dice**: 0.7482
    - **iou**: 0.5976
    - **precision**: 0.7114
    - **recall**: 0.7889
    - **mean_image_dice**: 0.703
    - **ms**: 41.8
  - **yolo_only**:
    - **dice**: 0.7323
    - **iou**: 0.5777
    - **precision**: 0.6918
    - **recall**: 0.7779
    - **mean_image_dice**: 0.6734
    - **ms**: 18.4
  - **hybrid_roi_gated**:
    - **dice**: 0.7454
    - **iou**: 0.5941
    - **precision**: 0.7121
    - **recall**: 0.782
    - **mean_image_dice**: 0.6988
    - **ms**: 42.1
  - **hybrid_dual_threshold**:
    - **dice**: 0.7489
    - **iou**: 0.5987
    - **precision**: 0.717
    - **recall**: 0.7839
    - **mean_image_dice**: 0.7035
    - **ms**: 56.9
- **paired_bootstrap_vs_unet**:
  - **hybrid_roi_gated**: WORSE (diff -0.0042, CI [-0.0076, -0.0008])
  - **hybrid_dual_threshold**: NO demonstrated improvement (diff +0.0005, CI [-0.0005, +0.0015])

## Known limitations
- No segmentation accuracy gain over the U-Net alone; the value is boxes + detection confidence.
- ROI-crop mode gave no speed gain on 640x360 images (ROIs cover most of the image); gains on large images are untested.
- Pooled metrics excluding leak-flagged images were reported incorrectly by the first evaluator version (bug fixed; only the mean-image-Dice sensitivity is valid: U-Net 0.7021 vs dual 0.7025).

## Not for
- Claims of improved segmentation accuracy
