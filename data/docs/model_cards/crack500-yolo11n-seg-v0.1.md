# Crack500 YOLO11n-Seg - crack localisation (experiment)

**ID:** `crack500-yolo11n-seg-v0.1`  
**Status:** EXPERIMENTAL v0.1 (not the segmentation model of record)  
**Evidence:** PARTLY VERIFIED: label conversion report and validation/test metrics from files; weights hash, training args and detection mAP not provided


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Crack localisation (boxes, confidence) and coarse instance masks

## Data
Crack500, labels converted from masks to YOLO polygons; official split preserved

## Architecture
Ultralytics YOLO11n-Seg (pretrained yolo11n-seg.pt), 1 class

## Checkpoint
- **path**: NEEDS VERIFICATION
- **sha256**: NEEDS VERIFICATION

## Training / configuration
- **script**: ml/hybrid/train_yolo_seg.py
- **defaults**: 100 epochs, imgsz 640, batch 16, patience 20, seed 42, cosine LR (check args.yaml: NEEDS VERIFICATION)
- **label_conversion**:
  - **polygons**: 7258
  - **dropped_tiny_components**: 1484
  - **polygon_vs_mask_iou_mean**: 0.9748
  - **polygon_vs_mask_iou_p05**: 0.9379
  - **share_below_0_8**: 0.0077

## Operating point
- **yolo_conf**: 0.25
- **chosen_on**: validation only

## Results
- **validation**:
  - **dice**: 0.8077
  - **iou**: 0.6774
  - **precision**: 0.7946
  - **recall**: 0.8212
  - **mean_image_dice**: 0.7412
- **test**:
  - **dice**: 0.7323
  - **iou**: 0.5777
  - **precision**: 0.6918
  - **recall**: 0.7779
  - **mean_image_dice**: 0.6734
  - **images_with_no_detection**: 13
  - **mean_inference_ms_T4**: 18.4
- **vs_unet_test_paired_bootstrap**:
  - **mean_image_dice_diff**: -0.0296
  - **ci95**: [-0.0371, -0.0221]
  - **verdict**: WORSE than U-Net
- **detection_map**: NOT YET MEASURED on Crack500 (run Ultralytics val once on the frozen best.pt and record box/mask mAP50, mAP50-95)

## Known limitations
- Masks are coarse (prototype masks at 1/4 input resolution); thin cracks lose detail.
- Mask-to-polygon conversion fills holes and drops components under 6 px.
- Do not compare with the Crack-seg demo model: different dataset.

## Not for
- Primary segmentation (use the U-Net)

## Pending verification
- best.pt SHA256 and args.yaml
- Box/mask mAP on the test split (one run, frozen weights)
