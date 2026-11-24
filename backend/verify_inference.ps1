# Run from the repo root:  .\verify_inference.ps1
$ErrorActionPreference = "Stop"
Set-Location C:\Users\lenovo\Documents\InfraScan-Infosys-Team-3
.\venv\Scripts\Activate.ps1

# Use real models only: U-Net-only close_up, no mock, hashes verified
Remove-Item Env:INFRASCAN_YOLO_CKPT, Env:CRACK_YOLO_CKPT, Env:ALLOW_MOCK_INFERENCE -ErrorAction SilentlyContinue
$env:DATABASE_URL = "sqlite:///./infrascan_local.db"
$env:VERIFY_MODEL_HASHES = "1"

Write-Host "`n== 1. New backend tests ==" -ForegroundColor Cyan
python -m pytest backend/tests/test_predictions_inference.py -v

Write-Host "`n== 2. Whole backend suite ==" -ForegroundColor Cyan
python -m pytest backend/tests -q

Write-Host "`n== 3. ML suite (expect 34 passed) ==" -ForegroundColor Cyan
python -m pytest data/ml -q

Write-Host "`n== 4. Live API check (start server in a 2nd window first) ==" -ForegroundColor Cyan
Write-Host "   python -m uvicorn backend.main:app --reload --reload-dir backend"
Read-Host "Press Enter when the server is running"

curl.exe -s http://127.0.0.1:8000/health/models | ConvertFrom-Json | ConvertTo-Json -Depth 6

$img = "data\rdd2022_yolo\images\test\India_000005.jpg"
$json = curl.exe -s -X POST http://127.0.0.1:8000/api/v1/predictions/analyze `
    -F "asset_id=1" -F "profile=road_scene" -F "file=@$img;type=image/jpeg"
$r = $json | ConvertFrom-Json
$d = $r.defect_details

"source            : $($d.source)"                       # must be 'model'
"profile           : $($d.profile)"
"conf used         : $($d.raw_inference.pipeline.config.conf)"   # 0.233
"warnings          : $($d.warnings -join ', ')"
"failure date      : $($r.predicted_failure_date)"       # must be empty
"class_counts      : D00=$($d.class_counts.D00) D10=$($d.class_counts.D10) D20=$($d.class_counts.D20) D40=$($d.class_counts.D40)"
$d.models | Format-Table role, id, sha256 -AutoSize         # sha256 must be 64 hex chars
$d.defects | ForEach-Object { "{0,-4} {1,-34} conf={2}  box=[{3},{4},{5},{6}]" -f $_.bounding_box.class_name, $_.defect_type, $_.bounding_box.confidence, $_.bounding_box.x_min, $_.bounding_box.y_min, $_.bounding_box.x_max, $_.bounding_box.y_max }
"overlay           : $($d.artifacts.overlay_uri)"

if ($d.source -ne "model" -or $d.class_counts.D00 -lt 1 -or $d.class_counts.D40 -lt 1) {
    Write-Host "FAIL: not real D00/D40 model output" -ForegroundColor Red
} else {
    Write-Host "PASS: real D00/D40 detections from the model" -ForegroundColor Green
}
