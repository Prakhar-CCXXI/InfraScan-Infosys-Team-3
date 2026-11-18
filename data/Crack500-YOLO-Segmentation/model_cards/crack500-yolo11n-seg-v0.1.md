# Crack500 YOLO11n-Seg - crack localisation (experiment)

**ID:** `crack500-yolo11n-seg-v0.1`  
**Status:** EXPERIMENTAL v0.1 (not the segmentation model of record)  
**Evidence:** Training args and per-epoch validation metrics VERIFIED_FROM_FILES (args.yaml, results.csv); weights SHA256 provided by the user (not independently verified); pixel-level val/test metrics from hybrid evaluation files; test mAP not measured


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Crack localisation (boxes, confidence) and coarse instance masks

## Data
Crack500, labels converted from masks to YOLO polygons; official split preserved

## Architecture
Ultralytics YOLO11n-Seg (pretrained yolo11n-seg.pt), 1 class

## Checkpoint
- **path**: Crack500-YOLO-Segmentation/checkpoints/best.pt (local copy of the Colab run crack500_yolo11n_seg_s42)
- **sha256**: 98e725d194678f0f58f800d2e2ca91b33c2c48a24c17465e7657eba6179cad69
- **note**: Hash provided by the user. The hybrid evaluation files did not record the YOLO checkpoint hash, so the link between this file and the hybrid results is unconfirmed (see pending).

## Training / configuration
- **platform**: Google Colab, GPU 0
- **ultralytics_args**:
  - **model**: yolo11n-seg.pt
  - **epochs**: 50
  - **patience**: 10
  - **batch**: 8
  - **imgsz**: 640
  - **optimizer**: AdamW
  - **lr0**: 0.002
  - **lrf**: 0.01
  - **cos_lr**: True
  - **weight_decay**: 0.0005
  - **warmup_epochs**: 3
  - **seed**: 42
  - **deterministic**: True
  - **amp**: True
  - **mask_ratio**: 4
  - **overlap_mask**: True
  - **mosaic**: 1.0
  - **close_mosaic**: 10
  - **scale**: 0.5
  - **translate**: 0.1
  - **fliplr**: 0.5
  - **workers**: 2
- **epochs_logged**: 50
- **best_epoch_by_fitness**: 47
- **note**: Values above are from args.yaml; they differ from train_yolo_seg.py defaults and from the batch/lr0 quoted in chat (batch 16, lr0 0.001).
- **label_conversion**:
  - **polygons**: 7258
  - **dropped_tiny_components**: 1484
  - **polygon_vs_mask_iou_mean**: 0.9748
  - **polygon_vs_mask_iou_p05**: 0.9379
  - **share_below_0_8**: 0.0077

## Operating point
- **yolo_conf**: 0.25
- **chosen_on**: validation only (pixel Dice)

## Results
- **validation_ultralytics_best_epoch47**:
  - **box**:
    - **precision**: 0.6908
    - **recall**: 0.4917
    - **mAP50**: 0.5384
    - **mAP50_95**: 0.359
  - **mask**:
    - **precision**: 0.6747
    - **recall**: 0.4756
    - **mAP50**: 0.5055
    - **mAP50_95**: 0.186
  - **note**: Instance-level matching (IoU thresholds) is harsh on thin, fragmented cracks and is NOT comparable with pixel Dice/IoU.
- **validation_pixel**:
  - **dice**: 0.8077
  - **iou**: 0.6774
  - **precision**: 0.7946
  - **recall**: 0.8212
  - **mean_image_dice**: 0.7412
- **test_pixel**:
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
- **test_detection_map**: NOT MEASURED (test images not available in the environment used for registry work)

## Known limitations
- Masks are coarse (prototype masks at 1/4 input resolution); thin cracks lose detail.
- Mask-to-polygon conversion fills holes and drops components under 6 px.
- Validation box mAP50 is 53.8% (recall 49.2%), far below the PDF's proposed 85% target; part of this is the metric's mismatch with thin cracks, but it is the measured value.
- Do not compare with the Crack-seg demo model: different dataset.

## Not for
- Primary segmentation (use the U-Net)

## Pending verification
- Confirm this best.pt is the file passed as --yolo-ckpt in the hybrid evaluation (re-hash in that environment)
- Box/mask mAP on the test split (one run, frozen weights)
