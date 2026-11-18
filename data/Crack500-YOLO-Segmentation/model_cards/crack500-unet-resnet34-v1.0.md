# Crack500 U-Net (ResNet34) - crack segmentation

**ID:** `crack500-unet-resnet34-v1.0`  
**Status:** FROZEN v1.0 (model of record for segmentation)  
**Evidence:** VERIFIED_FROM_FILES (metrics.json, test_metrics.json, config.json, checkpoint SHA256; test Dice re-derived independently by the hybrid evaluation)


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Pixel-level binary crack segmentation

## Data
Crack500 (official split: train 1,896 / val 348 / test 1,124 image-mask pairs)

## Architecture
segmentation_models_pytorch Unet, ResNet34 encoder (ImageNet-initialised), 1 output channel

## Checkpoint
- **path**: /kaggle/working/seg_runs/unet_resnet34_s42/best.pt
- **sha256**: 684484b1f408b3e3af18115613f9713a8ec8d62b5f697976a877a2614abc2163
- **size_bytes**: 97903743

## Training / configuration
- **crop**: 352
- **epochs**: 40
- **batch_size**: 8
- **lr**: 0.0003
- **optimizer**: AdamW (wd 1e-4), cosine schedule
- **loss**: BCE + Dice
- **precision**: AMP
- **early_stopping_patience**: 8
- **seed**: 42
- **manifest_md5**: 3c43cfc22afcf8a1954c14b0b3c1c58f
- **script**: ml/segmentation/train_seg.py

## Operating point
- **threshold**: 0.4
- **chosen_on**: validation only

## Results
- **validation_at_0_4**:
  - **dice**: 0.8206
  - **iou**: 0.6958
  - **precision**: 0.8065
  - **recall**: 0.8352
  - **mean_image_dice**: 0.7625
  - **boundary_f1_2_4_8px**: [0.4621, 0.6703, 0.8518]
- **test_at_0_4**:
  - **dice**: 0.7482
  - **iou**: 0.5976
  - **precision**: 0.7114
  - **recall**: 0.7889
  - **mean_image_dice**: 0.703
  - **boundary_f1_2_4_8px**: [0.3923, 0.5884, 0.7936]
- **architecture_comparison_val_dice**:
  - **unet_resnet34**: 0.8206
  - **deeplabv3plus_resnet34**: 0.8162
  - **unetplusplus_resnet34**: 0.8126
  - **unet_scse**: 0.8098
- **seeds_val_dice**:
  - **seed1**: 0.8109
  - **seed2**: 0.8158
  - **seed42**: 0.8206
  - **mean**: 0.8158
  - **sd**: 0.0048

## Known limitations
- Test Dice is about 7 points below validation Dice; report both.
- Architecture differences (<=0.8 pt) are within seed noise (SD 0.48 pt); U-Net was chosen for simplicity, not demonstrated superiority.
- Seed 42 was the best of 3 seeds, so its validation score is slightly optimistic; the test score is unaffected.
- Crack500 is pavement imagery; behaviour on concrete decks/walls is untested.
- Annotations are thick and coarse: boundary F1 is 39% at 2 px tolerance, 79% at 8 px.
- Official split has 80 images in source photos shared across splits (37 in test); sensitivity analysis shows no material effect on mean image Dice.
- Measurements derived from masks are in pixels only (no calibration).

## Not for
- Structural safety decisions
- Physical (mm) measurements without a calibrated scale

## Pending verification
- Confirm best.pt hash on the deployment copy
