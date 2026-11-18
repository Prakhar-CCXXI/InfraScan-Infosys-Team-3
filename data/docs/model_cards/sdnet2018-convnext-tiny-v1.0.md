# SDNET2018 ConvNeXt-Tiny - crack / no-crack patch classification

**ID:** `sdnet2018-convnext-tiny-v1.0`  
**Status:** v1.0 selected (statistically tied with DenseNet121)  
**Evidence:** Fold-0 comparison VERIFIED_FROM_FILES (sdnet_report.md, inventory.csv); thresholds and fold-0 test counts from a pasted metrics.json; five-fold summary REPORTED_NOT_VERIFIED


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Binary classification of 256x256 concrete patches (decks, pavements, walls)

## Data
SDNET2018, 56,092 images; photo-grouped 5-fold splits (group = surface + filename prefix); fold 0 used for model comparison

## Architecture
torchvision ConvNeXt-Tiny, ImageNet-initialised, single logit, two-phase fine-tuning, weighted BCE

## Checkpoint
- **path**: /kaggle/working/convnext_tiny_backup/best.pt (fold 0)
- **sha256**: NEEDS VERIFICATION

## Training / configuration
- **script**: ml/training/train_classifier.py
- **image_size**: NEEDS VERIFICATION
- **selection**: best validation PR-AUC

## Operating point
- **default**: validation recall-90% threshold (0.5058, fold 0)
- **alternative**: validation best-F1 threshold (0.8991, fold 0)
- **chosen_on**: validation only

## Results
- **fold0_test**:
  - **roc_auc**: 0.953
  - **pr_auc**: 0.886
  - **pr_auc_ci95_photo_bootstrap**: [0.847, 0.917]
- **fold0_test_at_recall90_thr**:
  - **precision**: 0.576
  - **recall**: 0.897
  - **f1**: 0.701
  - **false_alarm_rate**: 0.13
- **fold0_test_at_f1_thr**:
  - **precision**: 0.86
  - **recall**: 0.772
  - **f1**: 0.813
- **fold0_model_comparison_pr_auc**:
  - **convnext_tiny**: 0.886
  - **densenet121**: 0.884
  - **efficientnet_b0**: 0.877
  - **mobilenet_v3_large**: 0.867
  - **note**: ConvNeXt vs DenseNet diff -0.001 [-0.015,+0.010]: tie; MobileNetV3 lower by 0.018 [-0.030,-0.009]
- **five_fold_reported**:
  - **pr_auc**: 85.04 +/- 4.53 pp
  - **roc_auc**: 93.92 +/- 1.98 pp
  - **precision**: 45.63 +/- 10.48 pp
  - **recall**: 90.17 +/- 2.32 pp
  - **f1**: 59.94 +/- 9.35 pp
  - **caveat**: fold configurations were not controlled; files not re-verified
- **five_fold_false_alarm_rate_reported**:
  - **deck**: 0.272
  - **pavement**: 0.113
  - **wall**: 0.302

## Known limitations
- Fold 0 scores higher than the reported five-fold mean (PR-AUC 88.6 vs 85.0); quote both.
- At 90% recall, about 42% of alerts are false (precision 57.6% on fold 0, ~46% reported across folds).
- Blind audit (one fold, one non-expert reviewer): of 60 most-confident false positives, 28 looked like real cracks and 22 ambiguous; of 40 lowest-scoring 'cracked' images, 30 showed no crack. Tail samples only, not a dataset noise rate.
- Does not transfer from the Concrete Crack dataset; trained on SDNET2018 only.
- ResNet50 was excluded from the consolidated comparison: no verifiable output on the same test set (an earlier run used a different split, PR-AUC 0.805 not comparable).

## Not for
- Structural safety decisions
- Crack width/length measurement

## Pending verification
- Checkpoint hash and image size
- Fold 1-4 outputs if the five-fold table is to be re-verified
