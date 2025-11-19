# Script để check model status
Write-Host "`n=== MODEL STATUS CHECK ===" -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    $json = $response.Content | ConvertFrom-Json
    
    Write-Host "Backend: " -NoNewline
    Write-Host "RUNNING" -ForegroundColor Green
    
    Write-Host "Model Loaded: " -NoNewline
    if ($json.model_loaded) {
        Write-Host "YES" -ForegroundColor Green
        Write-Host "`nModel đã load! AI sẽ trả lời bằng model thật." -ForegroundColor Green
    } else {
        Write-Host "NO ⏳" -ForegroundColor Yellow
        Write-Host "`n⏳ Model đang load... (có thể mất 2-5 phút)" -ForegroundColor Yellow
        Write-Host "   → Kiểm tra terminal backend để xem progress" -ForegroundColor Cyan
        Write-Host "   → Hiện tại AI đang dùng mock response" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Backend không chạy hoặc không thể kết nối" -ForegroundColor Red
    Write-Host "   → Kiểm tra xem backend có đang chạy không" -ForegroundColor Yellow
}

Write-Host ""

