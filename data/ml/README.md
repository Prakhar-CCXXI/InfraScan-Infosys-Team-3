# InfraScan ML Pipeline

> Research prototype for inspection support. Outputs require qualified engineering review; not a structural safety assessment.

## Production Models (Registry of Record)

All model metadata, SHA-256 hashes, and limitations are tracked in `data/ml/registry/model_registry.json` and `data/docs/model_cards/`.

| Model ID | Task | Input Domain | Checkpoint | Operating Point | Key Test Metric |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `rdd2022-yolo11s-v1.0` | Road damage detection (`D00`, `D10`, `D20`, `D40`) | Wide street-view / dashcam | `yolo11s_rdd2022_s42/best.pt` | `imgsz=640` | mAP50: `0.357` (3-class mean: `0.448`) |
| `sdnet2018-convnext-tiny-v1.0` | Binary crack classification + Grad-CAM | Close-up concrete patches (256x256) | `convnext_tiny_sdnet2018/best.pt` | `0.5058` (90% recall) / `0.8991` (best F1) | Fold-0 PR-AUC: `0.886`, ROC-AUC: `0.953` |
| `crack500-unet-resnet34-v1.0` | Pixel-level binary crack segmentation | Close-up pavement crack images | `unet_resnet34_crack500/unet_best.pt` | `threshold=0.4` | Test Dice: `0.7482`, IoU: `0.5976` |

### Verified Weights (Google Drive)
- **Drive Folder:** https://drive.google.com/drive/folders/1UWV_bms_h4FcHoBwiblTqSLBBqj_ndY2?usp=sharing
- `rdd2022-yolo11s-v1.0` SHA-256: `848f619cdebacd7ae0b63a585bdec50939244cb520adc8b20b3c129a33c8bf43`
- `crack500-unet-resnet34-v1.0` SHA-256: `684484b1f408b3e3af18115613f9713a8ec8d62b5f697976a877a2614abc2163`
- `crack500-yolo11n-seg-v0.1` (experimental) SHA-256: `98e725d194678f0f58f800d2e2ca91b33c2c48a24c17465e7657eba6179cad69`

## Backend Routing Rules
- **Dashcam / street-view imagery** -> route to `rdd2022-yolo11s-v1.0`. Do **not** send wide street views to ConvNeXt-Tiny (causes false positives on sky/trees/power lines).
- **Close-up concrete/pavement imagery** -> route to `sdnet2018-convnext-tiny-v1.0` (classification + Grad-CAM via `data/ml/explain/gradcam_cli.py`) and `crack500-unet-resnet34-v1.0` (pixel mask + geometry/severity).
- **Measurements & Severity:** Geometry outputs are in **pixels** unless camera calibration is provided. Severity ratings carry `THRESHOLDS_NOT_VALIDATED` and `UNCALIBRATED_SCALE` flags.

## Running Tests & Rebuilding Registry

Run from the repository root (`InfraScan-Infosys-Team-3`):

```powershell
# Rebuild model_registry.json and all 7 model cards
python data\ml\registry\build_registry.py

# Run full ML test suite (27 tests)
$env:PYTHONPATH = "backend\services"
python -m pytest data\ml -q