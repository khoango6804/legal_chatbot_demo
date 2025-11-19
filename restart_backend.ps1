# Script để restart backend
Write-Host "`n=== RESTARTING BACKEND ===" -ForegroundColor Cyan
Write-Host ""

# Tìm và kill process cũ
Write-Host "Tìm process đang dùng port 8000..." -ForegroundColor Yellow
$processes = netstat -ano | findstr :8000 | Select-String "LISTENING"
if ($processes) {
    $pid = ($processes -split '\s+')[-1]
    Write-Host "Tìm thấy PID: $pid" -ForegroundColor Yellow
    Write-Host "Killing process..." -ForegroundColor Yellow
    taskkill /PID $pid /F 2>$null
    Start-Sleep -Seconds 2
    Write-Host "Process đã được kill" -ForegroundColor Green
} else {
    Write-Host "Không tìm thấy process nào đang dùng port 8000" -ForegroundColor Yellow
}

Write-Host ""

# Chạy backend mới
Write-Host "Starting backend..." -ForegroundColor Cyan
Write-Host ""

$backendPath = Join-Path $PSScriptRoot "backend"
Set-Location $backendPath

# Set environment variables
$env:MODEL_HF_REPO = "sigmaloop/qwen3-0.6B-instruct-trafficlaws"
$env:MODEL_HF_SUBFOLDER = "model"
$env:HF_TOKEN = "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"
$env:PORT = "8000"
$env:HOST = "0.0.0.0"

Write-Host "Environment variables set:" -ForegroundColor Green
Write-Host "  MODEL_HF_REPO: $env:MODEL_HF_REPO"
Write-Host "  MODEL_HF_SUBFOLDER: $env:MODEL_HF_SUBFOLDER"
Write-Host "  PORT: $env:PORT"
Write-Host ""

Write-Host "Model will be loaded from Hugging Face Hub" -ForegroundColor Yellow
Write-Host "This may take 2-5 minutes on first run..." -ForegroundColor Yellow
Write-Host ""

Write-Host "Starting Python backend..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

python app.py

