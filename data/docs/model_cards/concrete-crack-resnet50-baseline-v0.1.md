# Concrete Crack Images ResNet50 - binary baseline

**ID:** `concrete-crack-resnet50-baseline-v0.1`  
**Status:** BASELINE v0.1 (not for deployment)  
**Evidence:** REPORTED_IN_CHAT_JSON; split report VERIFIED_FROM_FILES (uploaded zips)


> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.


## Task
Binary crack/no-crack classification of 227x227 patches

## Data
Concrete Crack Images for Classification: 40,000 -> 38,402 after exact-duplicate removal; grouped split train 26,892 / val 5,773 / test 5,737

## Architecture
torchvision ResNet50, ImageNet-initialised

## Checkpoint
- **path**: NEEDS VERIFICATION
- **sha256**: NEEDS VERIFICATION

## Training / configuration
- **script**: ml/training/train_classifier.py

## Operating point
- **threshold**: 0.5

## Results
- **test**:
  - **accuracy**: 0.99895
  - **precision**: 0.99899
  - **recall**: 0.99899
  - **f1**: 0.99899
  - **auc_roc**: 0.99999
  - **confusion_matrix**: [[2763, 3], [3, 2968]]
- **external_sdnet2018**:
  - **accuracy**: 0.833
  - **precision**: 0.432
  - **recall**: 0.328
  - **f1**: 0.373
  - **auc_roc**: 0.707
  - **pr_auc**: 0.319

## Known limitations
- In-domain score is saturated (a 3-feature logistic regression reaches 96.7%); it says little about real performance.
- Fails on SDNET2018 (ROC-AUC 0.71): learned texture/contrast shortcuts.

## Not for
- Any deployment
- Evidence of real-world accuracy

## Pending verification
- Checkpoint path/hash if it is kept
