# RDD2022_India YOLO11s - road damage detection

**ID:** `rdd2022-yolo11s-v1.0`  
**Status:** FROZEN v1.0 (model of record for dashcam road damage detection)  
**Evidence:** VERIFIED_FROM_FILES (rdd2022_val_metrics.json, rdd2022_test_metrics.json, checkpoint SHA256)


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Multi-class bounding-box detection of road damage in street-view / dashcam imagery (D00 longitudinal crack, D10 transverse crack, D20 alligator crack, D40 pothole)

## Data
RDD2022_India converted to YOLO format (val 1,150 images / 1,068 boxes; test 1,200 images / 1,058 boxes)

## Architecture
Ultralytics YOLO11s (100 layers fused, 9,414,348 parameters, 21.4 GFLOPs), 4 classes (D00, D10, D20, D40)

## Checkpoint
- **path**: rdd2022_detection/checkpoints/yolo11s_rdd2022_s42/best.pt
- **sha256**: 848f619cdebacd7ae0b63a585bdec50939244cb520adc8b20b3c129a33c8bf43
- **size_mb**: 19.2

## Training / configuration
- **epochs_completed**: 82
- **imgsz**: 640
- **seed**: 42
- **runtime_hours_T4**: 2.349
- **script**: ml/detection/train_rdd2022_yolo.py
- **eval_script**: ml/detection/eval_rdd2022_yolo.py

## Operating point
- **imgsz**: 640
- **evaluation**: Ultralytics standard val/test COCO-style mAP

## Results
- **validation**:
  - **overall**:
    - **precision**: 0.45
    - **recall**: 0.35
    - **mAP50**: 0.355
    - **mAP50_95**: 0.154
  - **D00**:
    - **precision**: 0.464
    - **recall**: 0.344
    - **mAP50**: 0.298
    - **mAP50_95**: 0.122
    - **gt_boxes**: 262
    - **reliable**: True
  - **D10**:
    - **precision**: 0.28
    - **recall**: 0.059
    - **mAP50**: 0.083
    - **mAP50_95**: 0.045
    - **gt_boxes**: 17
    - **reliable**: False
  - **D20**:
    - **precision**: 0.532
    - **recall**: 0.617
    - **mAP50**: 0.624
    - **mAP50_95**: 0.3
    - **gt_boxes**: 308
    - **reliable**: True
  - **D40**:
    - **precision**: 0.522
    - **recall**: 0.383
    - **mAP50**: 0.416
    - **mAP50_95**: 0.151
    - **gt_boxes**: 481
    - **reliable**: True
- **test**:
  - **overall**:
    - **precision**: 0.364
    - **recall**: 0.392
    - **mAP50**: 0.357
    - **mAP50_95**: 0.151
  - **populated_3class_mean_mAP50**: 0.448
  - **D00**:
    - **precision**: 0.393
    - **recall**: 0.359
    - **mAP50**: 0.312
    - **mAP50_95**: 0.135
    - **gt_boxes**: 256
    - **reliable**: True
  - **D10**:
    - **precision**: 0.138
    - **recall**: 0.104
    - **mAP50**: 0.085
    - **mAP50_95**: 0.026
    - **gt_boxes**: 17
    - **reliable**: False
  - **D20**:
    - **precision**: 0.495
    - **recall**: 0.65
    - **mAP50**: 0.63
    - **mAP50_95**: 0.293
    - **gt_boxes**: 314
    - **reliable**: True
  - **D40**:
    - **precision**: 0.432
    - **recall**: 0.455
    - **mAP50**: 0.403
    - **mAP50_95**: 0.151
    - **gt_boxes**: 471
    - **reliable**: True
- **inference_speed_ms**:
  - **T4_GPU**: 5.0
  - **i3_6006U_CPU**: 451.2

## Known limitations
- Severe class imbalance on D10 (transverse cracks): only 17 boxes in val and 17 in test (flagged reliable=False); unweighted macro mAP50 is pulled down by ~9-10 points.
- Trained exclusively on Indian dashcam road imagery (RDD2022_India); performance on other regions, lighting conditions, or close-up structural concrete is untested.
- Bounding boxes only (no pixel-level segmentation masks or physical mm measurements).

## Not for
- Structural safety decisions
- Close-up concrete crack width/length measurement (use Crack500 U-Net)
