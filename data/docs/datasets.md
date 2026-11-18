# InfraScan AI/ML - Dataset Documentation and Comparison (Milestone 1)

Evidence: **V** = verified from files/outputs inspected during this work, **C** = numbers pasted from outputs, **R** = reported, not independently seen. Datasets are kept separate; their labels are never reused for a different task (e.g. image-level labels are never turned into masks, boxes are never turned into masks).

## 1. Summary and intended task
| Dataset | Label type | Size | Intended task in InfraScan | Used for | Evidence |
|---|---|---|---|---|---|
| Concrete Crack Images | Image-level crack / no crack | 40,000 (20k / 20k); 38,402 after duplicate removal | Binary classification baseline | ResNet50 baseline; showed that an easy dataset does not transfer | V |
| SDNET2018 | Image-level crack / no crack, surface D/P/W | 56,092 | Main crack classifier (concrete decks, pavements, walls) | ConvNeXt-Tiny v1.0 and the model comparison | V / C |
| Crack500 | Binary pixel masks | 3,368 pairs | Segmentation; geometry; detection comparison | U-Net v1.0, YOLO11n-Seg experiment, hybrid, geometry validation | V |
| Crack-seg | YOLO polygons, 1 class | 3,717 / 112 / 200 | Existing FastAPI demo only | Demo model (untouched) | R |
| RDD2022 (India) | Pascal VOC boxes, 10 class codes | 7,706 train (labelled) + 1,959 test (unlabelled) | Multi-class road damage detection (Milestone 3 per the PDF); possible crack-type labels | Inspected only, not trained | V |
| CrackForest (CFD) | Pixel masks | not inspected | PDF-listed segmentation dataset | Not used (optional external check for the U-Net) | - |

## 2. Per-dataset notes
**Concrete Crack Images.** 227x227 RGB patches. 1,598 exact duplicates removed; grouped split 26,892 / 5,773 / 5,737. Cracked patches are higher in contrast (mean 30.8 vs 8.7), sharper (Laplacian variance 104 vs 32) and darker (164 vs 182), so a 3-feature logistic regression reaches 96.7% test accuracy: the dataset is saturated. A ResNet50 scores 99.9% in-domain but ROC-AUC 0.71 / PR-AUC 0.32 on SDNET2018.

**SDNET2018.** 256x256 patches cut from 230 source photos (deck 54, pavement 104, wall 72; 232 to 260 crops each); the filename prefix identifies the photo, so splits are grouped by surface + prefix. Deck 13,620 images (2,025 cracked), pavement 24,334 (2,608), wall 18,138 (3,851); 8,484 cracked overall (15.1%). Labels are noisy: in a blind audit of one fold's most confident false positives, 28 of 60 looked like real cracks and 22 were ambiguous (single non-expert reviewer; tail sample, not a dataset noise rate). Original labels were not changed.

**Crack500.** Official split 1,896 / 348 / 1,124; every image has a binary PNG mask (checked: sizes equal, values 0/1). Images are mostly 640x360 pavement photos. Mean crack-pixel fraction 6.4% / 5.7% / 5.6% (train/val/test). Leakage audit (source photo assumed = date_time prefix): 442 photos, 6 span splits (80 images, 37 in test), 4 filenames appear in both train and test, no exact duplicate images. Official split preserved; sensitivity analysis shows no material effect. Masks are thick and loosely drawn (boundary F1 39% at 2 px, 79% at 8 px).

**Crack-seg (demo).** Separate dataset and model; not comparable with Crack500.

**RDD2022 India (inspected from files).** Folders: `train/images` (7,706), `train/annotations/xmls` (7,706), `test/images` (1,959, **no annotations**). All images are 720x720. Pascal VOC XML. Integrity: every train image has an XML, no XML without image, no size mismatches, no invalid, out-of-bounds or duplicate boxes, no unreadable images. 8,203 boxes; **3,921 images (50.9%) have no objects**; the 3,785 labelled images average 2.17 boxes (max 14). 33 boxes are tiny (< 0.1% of the image). Perceptual-hash check: 7 near-duplicate groups, 2 spanning train and test. Image numbering runs 0 to 9,891 with no group identifier. A visual check of 12 random images showed plausible but coarse boxes on dashcam road scenes (front view, sky, vehicles, bonnet).

## 3. RDD2022 India class distribution (V)
| Code | Boxes | Share | Images | Median box area (share of image) | Meaning (from RDD documentation, from memory - verify) |
|---|---|---|---|---|---|
| D40 | 3,187 | 38.9% | 1,530 | 0.9% | other corruption (rutting, bump, pothole, separation) |
| D20 | 2,021 | 24.6% | 1,758 | 9.6% | alligator crack |
| D00 | 1,555 | 19.0% | 1,109 | 1.7% | longitudinal crack (wheel-mark part) |
| D44 | 1,062 | 12.9% | 869 | 1.3% | white-line blur (road marking) |
| D01 | 179 | 2.2% | 118 | 1.7% | longitudinal crack (construction joint) |
| D10 | 68 | 0.8% | 60 | 1.8% | transverse crack |
| D43 | 57 | 0.7% | 57 | 8.4% | crosswalk blur (road marking) |
| D11 | 45 | 0.5% | 36 | 3.2% | transverse crack (construction joint) |
| D50 | 28 | 0.3% | 28 | 0.7% | utility hole |
| D0w0 | 1 | 0.01% | 1 | 3.8% | label typo, discard |

Grouped: longitudinal (D00+D01) 1,734; transverse (D10+D11) **113**; alligator 2,021; D40 3,187; markings and utility holes (D43, D44, D50) 1,147 (14%). Imbalance: D40 vs D10 is about 47:1, D40 vs D50 about 114:1. **Viability:** clean and consistently formatted, large enough for a YOLO detector on D00, D20, D40; transverse cracks (113 boxes) are too few for reliable per-class evaluation; D43/D44/D50 are not structural damage and fall outside the PDF's damage categories; the test split is unlabelled, so a validation/test split must be carved from train, preferably in contiguous filename blocks because adjacent frames are probably near-duplicates. Box labels cannot support segmentation masks or crack width/length measurement.

## 4. Mapping to the PDF
| PDF requirement | Dataset |
|---|---|
| Crack / no-crack classification | SDNET2018 (main), Concrete Crack (baseline) |
| Crack segmentation, geometry | Crack500 |
| Crack detection (YOLO) | Crack500 (converted masks), Crack-seg (demo) |
| Crack type (longitudinal, transverse, alligator) | RDD2022 has box labels for these types; **deliberately not used in Milestone 2** (decision: deferred to Milestone 3; transverse class too rare) |
| Multi-class surface damage (potholes, deformation, ...) | RDD2022 (roads only); no dataset yet for spalling, corrosion, exposed reinforcement, delamination, leakage |

## 5. Gaps
- No labelled data for concrete-structure damage beyond cracks (spalling, corrosion, exposed rebar).
- No dataset with physical scale, so no millimetre measurements.
- No expert-reviewed labels or severity annotations (needed for Milestone 3 severity).

## 6. RDD2022 India: converted dataset (V, from conversion_report.json)
Policy: D00+D01 -> D00, D10+D11 -> D10, D20, D40 kept; D43 (57), D44 (1,062), D50 (28) and the typo class D0w0 (1) dropped (1,148 boxes); 7,055 boxes kept; 8,203 in the XML in total (all accounted for). Images are kept (4,388 are background after dropping, 467 more than before because some contained only dropped classes).
| Split | Images | Empty | D00 | D10 | D20 | D40 |
|---|---|---|---|---|---|---|
| train | 5,356 | 3,034 | 1,216 | 79 | 1,399 | 2,235 |
| val | 1,150 | 668 | 262 | 17 | 308 | 481 |
| test | 1,200 | 686 | 256 | 17 | 314 | 471 |
Split method: blocks of 50 consecutive images, blocks linked by identical-hash images merged (6 merges, largest unit 150 images), greedy assignment by class. The adjacency diagnostic found consecutive frames are NOT more similar than random pairs (median dHash distance 26 bits for both), so block splitting was not needed for adjacency but is harmless; exact duplicates are kept together. D10 has only 17 boxes each in val and test, so its per-class metrics are unreliable.
