# Crack-seg YOLO11n-Seg - existing FastAPI demo model

**ID:** `crack-seg-yolo11n-demo-v0`  
**Status:** DEMO v0 (preserved unchanged)  
**Evidence:** App code VERIFIED_FROM_FILES (app.py, scripts, README); training metrics REPORTED_NOT_VERIFIED (no results.csv provided)


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Demo crack detection + masks inside the FastAPI intake app

## Data
Crack-seg dataset (train 3,717 / val 112 / test 200); NOT Crack500

## Architecture
Ultralytics YOLO11n-Seg, 1 class ('crack')

## Checkpoint
- **path**: runs/infrascan_demo/crack_seg_baseline/weights/best.pt
- **sha256**: NEEDS VERIFICATION

## Training / configuration
- **epochs**: 3
- **imgsz**: 320
- **batch**: 2
- **device**: cpu
- **script**: scripts/train_demo.py

## Operating point
- **confidence**: 0.25

## Results
- **reported**:
  - **box_map50**: 0.666
  - **box_map50_95**: 0.365
  - **mask_map50**: 0.54
  - **mask_map50_95**: 0.175

## Known limitations
- 3 epochs on CPU at 320 px: a pipeline demonstration, not a quality benchmark.
- Not comparable with Crack500 models (different data).
- Demo quality checks: brightness<45, Laplacian variance<60; the blur rule mislabels smooth concrete (uncracked concrete patches average ~32) and depends on resolution.
- Stored 'original' is re-encoded to JPEG; README text still says ai_prediction 'not_run'; page text mentions normalisation that the code does not perform.

## Not for
- Production use

## Pending verification
- results.csv, args.yaml, weights hash
