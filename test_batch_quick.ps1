# Quick Batch Processing Demo (OCR-free mode)
Write-Host "`n=== Batch Processing Demo ===" -ForegroundColor Cyan

# Test with OCR disabled for speed
$body = @{
    screenshot_paths = @(0..15 | ForEach-Object { "/data/test_frames/frame_$($_.ToString('00')).png" })
    model_type = "gemini"  # Use fast Gemini API instead of slow BLIP-2
    context = @{ mode = "ai_gameplay" }
} | ConvertTo-Json

Write-Host "Testing fast batch analysis (Gemini API mode)..." -ForegroundColor Yellow
$start = Get-Date

try {
    $result = Invoke-RestMethod -Uri "http://localhost:8006/analyze/batch" `
        -Method Post -Body $body -ContentType "application/json" -TimeoutSec 30
    
    $duration = ((Get-Date) - $start).TotalSeconds
    
    Write-Host "`n✅ Success in $([math]::Round($duration, 1))s!" -ForegroundColor Green
    $result | ConvertTo-Json -Depth 3
    
} catch {
    Write-Host "`n⚠️  BLIP-2 mode is too slow (~60-90s per image)" -ForegroundColor Yellow
    Write-Host "This is expected on CPU. Solutions:" -ForegroundColor Gray
    Write-Host "1. Use Gemini API for real-time analysis (fast)" -ForegroundColor White
    Write-Host "2. Run BLIP-2 on GPU (20x faster)" -ForegroundColor White  
    Write-Host "3. Use frame sampling (analyze 1-2 FPS instead of 16 FPS)" -ForegroundColor White
    Write-Host "`nError: $_" -ForegroundColor Red
}
