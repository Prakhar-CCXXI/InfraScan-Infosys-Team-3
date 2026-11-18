# InfraScan AI/ML - Consolidated Evaluation Report (Milestones 1-2)

*Research prototype for inspection support. Outputs require qualified engineering review and are not structural safety assessments.*
Evidence levels: **V** = verified from uploaded files, **C** = pasted JSON/chat only, **R** = reported, not verified. Model details: `docs/model_cards/`, registry: `ml/registry/model_registry.json`.

## 1. Datasets and their roles (kept separate)
| Dataset | Task | Split | Notes |
|---|---|---|---|
| Concrete Crack Images (40,000) | Binary classification baseline | 38,402 after exact-duplicate removal; train/val/test 26,892 / 5,773 / 5,737 (V) | In-domain score saturated; does not transfer |
| SDNET2018 (56,092; D/P/W) | Main classifier | Photo-grouped 5-fold (group = surface + filename prefix) | 8,484 cracked (15.1%) |
| Crack500 (3,368) | Segmentation, detection comparison | Official 1,896 / 348 / 1,124 (V) | Binary masks; mostly 640x360 pavement images |
| Crack-seg (3,717/112/200) | Existing YOLO demo only | - | Not comparable with Crack500 |
| RDD2022 | Multi-class road damage | - | Not inspected yet (Milestone 1 gap) |

**Leakage audit (Crack500):** 442 source photos (date_time prefix, an assumption); 6 span splits = 80 images (37 test, 36 train, 7 val); 4 filenames appear in both train and test; 0 exact duplicate images. Official split kept; flagged images analysed separately.

## 2. Classification
**Concrete Crack ResNet50 (C):** test accuracy 99.90%, F1 99.90%. A logistic regression on three image statistics reached 96.7%, so this dataset is easy. External test on SDNET2018: ROC-AUC 0.71, PR-AUC 0.32, recall 33% at 0.5. Conclusion: not usable on real surfaces.

**SDNET2018 fold-0 comparison (V; identical test set confirmed by label vector; intervals resample whole photos):**
| Model | ROC-AUC | PR-AUC [95% CI] | vs ConvNeXt | Precision / recall at val recall-90 thr | False-alarm rate |
|---|---|---|---|---|---|
| ConvNeXt-Tiny | 0.953 | 0.886 [0.847, 0.917] | reference | 0.576 / 0.897 | 13.0% |
| DenseNet121 | 0.952 | 0.884 [0.846, 0.918] | -0.001 [-0.015, +0.010] (tie) | 0.550 / 0.897 | 14.4% |
| EfficientNet-B0 | 0.946 | 0.877 [0.836, 0.912] | -0.009 [-0.022, +0.001] | 0.525 / 0.891 | 15.8% |
| MobileNetV3-Large | 0.942 | 0.867 [0.827, 0.902] | -0.018 [-0.030, -0.009] | 0.542 / 0.878 | 14.6% |

ResNet50 is excluded: no verifiable output on this test set (an earlier run used a different split; PR-AUC 0.805 is not comparable). **Selected: ConvNeXt-Tiny v1.0**, statistically tied with DenseNet121 (the lighter alternative).
**Operating point** (validation-selected): recall-90% threshold gives precision 57.6%, recall 89.7%, F1 70.1%; best-F1 threshold gives 86.0% / 77.2% / 81.3% (fold 0, C).
**Five folds (R, not controlled):** PR-AUC 85.0 +/- 4.5 pp, recall 90.2 +/- 2.3, precision 45.6 +/- 10.5. Fold 0 is better than the five-fold mean; quote both. Reported pooled false-alarm rates: deck 27%, pavement 11%, wall 30%.
**Label audit (one fold, one non-expert reviewer, R):** of the 60 most confident false positives, 28 looked like cracks and 22 were ambiguous; of the 40 lowest-scoring "cracked" images, 30 showed no crack; controls 1/40 and 1/20. These are tail samples, so they do not give a dataset noise rate. Original labels were not changed.

## 3. Segmentation and detection on Crack500 (V)
**U-Net ResNet34 (selected, threshold 0.4 from validation):** val Dice 82.06 / IoU 69.58; **test Dice 74.82, IoU 59.76, precision 71.14, recall 78.89, mean image Dice 70.30**; boundary F1 at 2/4/8 px: 39.2 / 58.8 / 79.4. Architecture comparison (val Dice): U-Net 82.06, DeepLabV3+ 81.62, U-Net++ 81.26, U-Net+scSE 80.98; seeds 81.09 / 81.58 / 82.06 (SD 0.48), so the architecture gaps are within noise.

**YOLO and hybrid (test set evaluated once; frozen configs chosen on validation, 144-config grid):**
| Method | Dice | IoU | Precision | Recall | Mean image Dice | ms (T4) | Paired verdict vs U-Net |
|---|---|---|---|---|---|---|---|
| U-Net | 74.82 | 59.76 | 71.14 | 78.89 | 70.30 | 41.8 | baseline |
| YOLO11n-Seg only | 73.23 | 57.77 | 69.18 | 77.79 | 67.34 | 18.4 | WORSE (-2.96 pt, CI -3.7 to -2.2) |
| Hybrid, ROI-crop | 74.54 | 59.41 | 71.21 | 78.20 | 69.88 | 42.1 | WORSE (-0.42 pt, CI -0.76 to -0.08) |
| Hybrid, dual-threshold | 74.89 | 59.87 | 71.70 | 78.39 | 70.35 | 56.9 | No demonstrated improvement (+0.05 pt, CI -0.05 to +0.15) |

YOLO found no crack in 13 of 1,124 images. Instance-level test metrics (Ultralytics, reported): box precision/recall 0.515/0.338, mAP50 0.321, mAP50-95 0.178; mask mAP50 0.214, mAP50-95 0.061, far below validation (box mAP50 0.538, mask 0.506), a larger drop than the pixel Dice (0.808 to 0.732). Three inspected panels (hybrid, no-detection cases) showed that the no-detection images contain only tiny crack fragments cut by the image border. Hybrid fusion is a gating rule (U-Net probability thresholded inside the YOLO region, stricter outside), not a plain OR. **Conclusion: the hybrid does not improve segmentation accuracy.** The U-Net stays the segmentation model of record; YOLO's contribution is boxes and detection confidence, at +15 ms (dual-threshold). ROI-crop gave no speed gain on 640x360 images. Excluding the 37 leak-flagged test images changes mean image Dice by about 0.001 (U-Net 0.7021, dual 0.7025). Pooled metrics excluding flagged images in the first `test_results.json` are invalid (evaluator bug, now fixed); do not quote them.

**Geometry validation (V; validation split, U-Net masks at 0.4 vs annotated masks, pixel units, 348 images, 5 empty predictions counted as -100%):**
| Measure | Median signed error | Median abs error | Within +/-20% | Within +/-50% | Spearman |
|---|---|---|---|---|---|
| Length | -10.7% | 14.2% | 61.8% | 92.0% | 0.915 |
| Mean width | +16.8% | 21.8% | 46.0% | 80.5% | 0.801 |
| Max width | +6.8% | 15.7% | 58.3% | 87.9% | 0.822 |
| Area | +6.2% | 15.7% | 56.3% | 85.1% | 0.930 |

Lengths are underestimated and widths overestimated (consistent: area error is roughly the product). Rankings agree well, absolute values only roughly. The reference is the annotation, which has its own uncertainty, so this is agreement with annotated masks, not accuracy against physical cracks. No millimetre claims without a calibrated scale. **Where the errors come from:**
- **Orientation is reliable:** median error 1.1 degrees, 89% within 10 degrees (343 images).
- **Systematic bias even for good masks:** at Dice >= 0.8 (53% of images) length is still -10% and mean width +15%, so part of the error is the measurement method or annotation style (a likely cause, not yet tested: ragged annotation edges add skeleton spurs to ground-truth length), not segmentation failure. Area is the most robust size measure there (median +5%, 86% within 20%, Spearman 0.99).
- **Thin cracks:** 'thin' = lowest tercile of ground-truth mean width (< 12.75 px; terciles split at 12.75 and 21.39 px on 640x360 images). Mean width median +36%, only 28% within 20% (Spearman 0.58). This is a ~3-4 px overestimate, too large to be pixel quantisation; a likely cause (hypothesis, untested) is that predicted masks are thicker than the annotation on the thinnest cracks. Medium cracks rank poorly (Spearman 0.40); thick cracks are best (+7%, 64% within 20%).
- **Failed segmentations:** where Dice < 0.5 (6% of images) geometry is meaningless (length -70%, area -82%).
- Recommended primary measures: length, area and orientation; report mean/max width as approximate, and flag thin cracks as low-reliability.

## 4. Status against the PDF's proposed targets (section 10; targets, not validated results)
| Target | Result |
|---|---|
| Detection mAP@50 >= 85%, recall >= 90% | **Not met on validation**: Crack500 YOLO11n-Seg box mAP50 53.8%, box recall 49.2%, mask mAP50 50.6% (Ultralytics, best epoch 47, V). Test (reported): box mAP50 32.1%, recall 33.8%; mask mAP50 21.4%, mAP50-95 6.1%. Instance-level matching is harsh on thin, fragmented cracks and is not comparable with pixel Dice. Demo model (different data): box mAP50 66.6% (R) |
| Segmentation Dice >= 85%, IoU >= 75% | **Not met**: test 74.8 / 59.8 (validation 82.1 / 69.6) |
| Classification macro F1 >= 85% | Crack-class F1 81.3% at the best-F1 threshold (fold 0); macro F1 not computed |
| Recall >= 90% (classification) | 89.7% at the recall-90 threshold, with 57.6% precision |
| Inference < 3 s per image | Met (U-Net 42 ms on a T4 for 640x360 images) |
| Measurement uncertainty | First empirical estimate in section 3 (pixels, vs annotated masks); calibrated physical units not available |
| Severity validation | Not started (Milestone 3; needs engineer-defined criteria) |

## 5. Limitations
- Crack500 is pavement imagery; no evidence yet for concrete decks and walls (SDNET has no masks).
- Test Dice is about 7 points below validation Dice; the test set is larger (1,124 vs 348 images).
- SDNET labels are noisy and ambiguous; fold configurations were not controlled.
- No physical (mm) measurements without calibration; crack-type classification deferred (no labelled data); severity thresholds need engineer-defined criteria (Milestone 3).
- Existing demo: stored originals are JPEG re-encodes; blur rule (Laplacian < 60) flags smooth concrete; documentation is partly stale (see model card).

## 6. Open items
1. Crack500 YOLO: test mAP is reported (box 32.1 / mask 21.4); confirm that the weights used for it match the hashed `best.pt` (SHA256 98e725d1...cad69, trained on Colab: 50 epochs, batch 8, lr0 0.002) is the file used in the hybrid evaluation.
2. SDNET: checkpoint hash and image size; fold 1-4 files only if the five-fold table must be re-verified.
3. Reusable preprocessing module; API contract (include the measurement uncertainty above); RDD2022 inspection.
