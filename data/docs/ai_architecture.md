# InfraScan AI/ML - Architecture Note (Milestones 1-2)

Scope: the AI/ML component only (the backend, database and application are built separately). Milestone 3-4 features (severity, explainability, maintenance, mapping, reporting) are out of scope except as listed in section 6. Outputs are advisory and need qualified engineering review; they are not structural safety assessments.

## 1. Pipeline
```
Upload (JPEG/PNG/WebP)
  -> Pre-processing  [ml/preprocessing/image_preprocessing.py]
       validate (type, size, decode, min side) | quality flags (low light, blur; advisory) | resize (longest side <= 1280) | tiling helpers
  -> Segmentation    [U-Net ResNet34, ml/segmentation + ml/hybrid/hybrid_pipeline.py]
       probability map -> binary mask (threshold 0.4, chosen on validation); tiled for large images
  -> Localisation (optional)  [YOLO11n-Seg]
       boxes + detector confidence; hybrid fusion = YOLO gates where the U-Net is trusted (not a plain OR)
  -> Geometry (pixels)  [ml/hybrid/geometry.py]
       skeleton length, mean/max width, area, density, orientation, components, branch points
  -> Result builder  [ml/hybrid/inference_output.py]  -> docs/api_contract/inference_result.schema.json
  -> Backend: stores mask/overlay, fills uri fields, database, API (separate team)

Separate model, not yet wired in:  Patch classifier [ConvNeXt-Tiny, SDNET2018]  crack / no crack on 256x256 patches (needs a tiling + aggregation policy)
Milestone 3 additions (advisory, config-driven):
  Severity engine  [ml/severity/severity_engine.py + severity_config.json]  relative measures + detector classes -> category, score, suggested priority, flags
  Explainability   [ml/explain/gradcam.py]  Grad-CAM / Grad-CAM++ for the classifier and the U-Net (hooks need a GPU smoke test)
  Road-damage detector (RDD2022: D00, D10, D20, D40)  [ml/data/prepare_rdd2022_yolo.py, ml/detection/*]  trained: YOLO11s, test mAP50 0.357 (D10 unreliable)
Milestone 4 wrapper:
  Unified service  [ml/service/inference_service.py]  analyze(bytes, profile) -> schema-valid result; profile close_up (U-Net[+YOLO], geometry, severity, optional classifier) or road_scene (RDD2022 detector, severity); verifies checkpoint hashes against the registry
```

## 2. Datasets -> tasks -> models
| Task | Dataset | Model of record | Registry id |
|---|---|---|---|
| Crack / no-crack patch classification | SDNET2018 | ConvNeXt-Tiny v1.0 (tied with DenseNet121) | `sdnet2018-convnext-tiny-v1.0` |
| Pixel segmentation, geometry | Crack500 | U-Net ResNet34 v1.0 | `crack500-unet-resnet34-v1.0` |
| Localisation (boxes + confidence) | Crack500 (masks converted to polygons) | YOLO11n-Seg v0.1 (experimental) | `crack500-yolo11n-seg-v0.1` |
| Optional fused output | Crack500 | Hybrid v0.1 (no accuracy gain) | `crack500-hybrid-v0.1` |
| Existing demo | Crack-seg | YOLO11n-Seg demo v0 (untouched) | `crack-seg-yolo11n-demo-v0` |
| Baseline / negative result | Concrete Crack Images | ResNet50 v0.1 (not deployable) | `concrete-crack-resnet50-baseline-v0.1` |
| Multi-class road damage (D00, D10, D20, D40) | RDD2022 India, converted; val/test carved from train | YOLO11s detector v1.0 | `rdd2022-yolo11s-v1.0` |

## 3. Key results (details in docs/evaluation_report.md)
Crack500 U-Net test: Dice 74.8, IoU 59.8, precision 71.1, recall 78.9 (validation Dice 82.1). Hybrid vs U-Net on test: no demonstrated improvement; YOLO alone is worse (-3.0 pt mean image Dice); inference on a T4: U-Net 42 ms, YOLO 18 ms, hybrid 42 to 57 ms. SDNET2018 fold 0 (ConvNeXt): PR-AUC 0.886; at the validation recall-90% threshold recall 0.897, precision 0.576. Geometry vs annotated masks: orientation reliable (1.1 deg), area robust, length -11%, mean width +17%. The PDF's proposed targets (Dice >= 85, IoU >= 75, detection mAP@50 >= 85) are not met.

## 4. Design decisions and why
| Decision | Reason |
|---|---|
| U-Net is the segmentation model of record | Hybrid and YOLO-only did not beat it on test; architecture differences were within seed noise (SD 0.48 pt), so the simplest was kept |
| YOLO kept optional (boxes + confidence) | The PDF asks for detection output; it adds about 15 ms and no mask accuracy |
| Measurements in pixels with an uncertainty block | No calibration exists; validation shows systematic bias; mm only if a calibrated scale is supplied |
| Thresholds and models selected on validation only; test evaluated once per frozen model | Avoids optimistic reporting; the evaluator refuses a second test run |
| Photo-grouped splits and leakage audits | Crops of one photo must not cross splits (SDNET, Crack500) |
| Classifier not in the inference result yet | Patch-level model; aggregating patches to an image-level statement is undesigned |
| Severity and Grad-CAM deferred (Milestone 3) | The PDF requires severity thresholds validated against engineering standards; Grad-CAM exists only as an inspection of the SDNET classifier |
| Existing FastAPI demo left unchanged | Working code; the new preprocessing module can replace its checks later |

## 5. Open decisions
1. **Crack type: DECIDED, Option A (deferred).** RDD2022 India has box labels for longitudinal (1,734), transverse (113) and alligator (2,021) cracks plus D40 'other corruption' (3,187), but transverse cracks are too rare for reliable per-class results and the labels are road-scene boxes, not crack masks. RDD2022 is documented as the Milestone 3 multi-class detection dataset; no crack-type classifier is trained in Milestone 2. A documented orientation heuristic from segmentation masks remains possible and would be labelled as not a semantic classifier.
1b. **Milestone 3 decisions (confirmed by the team).** (a) RDD2022 detector classes: keep D00 (+D01), D10 (+D11), D20, D40; drop D43, D44, D50 and the D0w0 typo (implemented in `ml/data/prepare_rdd2022_yolo.py`). (b) Severity: no engineer or calibrated images are available, so the rule-based engine uses relative measures (normalised width quantiles, crack area density, detection class) from a config file whose schema can take millimetre thresholds later; every rating carries a low-confidence / uncalibrated-scale flag. (c) Priority: RDD2022 detector, Grad-CAM, severity engine; SegFormer comparison only if GPU quota remains.
2. **Classifier integration.** Define how patch predictions aggregate to an image (tiling, max or top-k, operating point) before adding the `classification` field.
3. **Thin-crack width flag.** Needs the lower tercile of predicted mean widths.

## 6. Dependencies for Milestones 3-4
Severity needs engineer-defined criteria and (for physical units) a calibration source; multi-class damage needs RDD2022 training or a concrete-defect dataset (none identified); explainability can extend the existing Grad-CAM inspection; geospatial, reporting and notifications belong to the backend.

## 7. Known weak points
Segmentation and detection scores are below the PDF's proposed targets; Crack500 is pavement imagery with thick, loosely drawn masks; SDNET labels are noisy; the five-fold SDNET results were not run under one controlled configuration; checkpoints other than the U-Net are not hash-verified for the SDNET and baseline models; only a few real inspection photos have been tested (none for concrete walls or decks with masks).
