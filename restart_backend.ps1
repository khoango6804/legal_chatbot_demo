# Script để restart backend
Write-Host "`n=== RESTARTING BACKEND ===" -ForegroundColor Cyan
Write-Host ""

# Tìm và kill process cũ
Write-Host "Tìm process đang dùng port 8100..." -ForegroundColor Yellow
$processes = netstat -ano | findstr :8100 | Select-String "LISTENING"
if ($processes) {
    $foundPid = ($processes -split '\s+')[-1]
    Write-Host "Tìm thấy PID: $foundPid" -ForegroundColor Yellow
    Write-Host "Killing process..." -ForegroundColor Yellow
    taskkill /PID $foundPid /F 2>$null
    Start-Sleep -Seconds 2
    Write-Host "Process đã được kill" -ForegroundColor Green
} else {
    Write-Host "Không tìm thấy process nào đang dùng port 8100" -ForegroundColor Yellow
}

Write-Host ""

# Chạy backend mới
Write-Host "Starting backend..." -ForegroundColor Cyan
Write-Host ""

$backendPath = Join-Path $PSScriptRoot "backend"
Set-Location $backendPath

# Set environment variables
$env:MODEL_PATH = Join-Path $PSScriptRoot "models\qwen3-0.6B-instruct-trafficlaws\model"
if (-not (Test-Path $env:MODEL_PATH)) {
    Write-Host "WARNING: Local model path $env:MODEL_PATH not found. Falling back to Hugging Face settings if provided." -ForegroundColor Yellow
} else {
    Write-Host "Using local model path: $env:MODEL_PATH" -ForegroundColor Green
}
Remove-Item Env:MODEL_HF_REPO -ErrorAction SilentlyContinue
Remove-Item Env:MODEL_HF_SUBFOLDER -ErrorAction SilentlyContinue
$env:PORT = "8100"
$env:HOST = "0.0.0.0"

Write-Host "Environment variables set:" -ForegroundColor Green
Write-Host "  MODEL_PATH: $env:MODEL_PATH"
Write-Host "  PORT: $env:PORT"
Write-Host ""

Write-Host "Model will be loaded from local path if available." -ForegroundColor Yellow
Write-Host "Ensure the folder contains config/tokenizer/model weights." -ForegroundColor Yellow
Write-Host ""

Write-Host "Starting Python backend..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python app.py

