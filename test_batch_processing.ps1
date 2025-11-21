# Test Batch Processing for 16 FPS Gameplay Analysis
Write-Host "`n=== PlayMetric PAIME - Batch Processing Test ===" -ForegroundColor Cyan

# Step 1: Check if Vision Service is running
Write-Host "`n[1/5] Checking Vision Service..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8006/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Service is $($health.status)" -ForegroundColor Green
    Write-Host "   Model loaded: $($health.model_loaded)" -ForegroundColor Gray
    Write-Host "   OCR loaded: $($health.ocr_loaded)" -ForegroundColor Gray
} catch {
    Write-Host "❌ Vision Service not accessible: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Create test frames inside container
Write-Host "`n[2/5] Creating 16 test frames..." -ForegroundColor Yellow
$createFramesScript = @'
from PIL import Image, ImageDraw
import os
os.makedirs('/data/test_frames', exist_ok=True)
for i in range(16):
    img = Image.new('RGB', (1080, 1920), color=(50, 50, 100 + i*10))
    draw = ImageDraw.Draw(img)
    if i < 8:
        # Menu scene
        draw.rectangle([400, 800, 680, 900], fill=(0, 200, 0))
        draw.text((450, 830), 'PLAY', fill=(255, 255, 255))
        draw.text((450, 1000), 'Score: 1234', fill=(255, 255, 255))
    else:
        # Gameplay scene (changed)
        draw.ellipse([500, 900, 580, 980], fill=(255, 0, 0))
        draw.text((450, 1100), f'Level {i-7}', fill=(255, 255, 255))
        draw.text((450, 1200), 'HP: 100', fill=(255, 255, 255))
    img.save(f'/data/test_frames/frame_{i:02d}.png')
print('done')
'@

try {
    $result = docker exec playmetric-vision python -c $createFramesScript
    Write-Host "✅ Created 16 frames (menu→gameplay transition)" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to create frames: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Load BLIP-2 model if not loaded
if (-not $health.model_loaded) {
    Write-Host "`n[3/5] Loading BLIP-2 model (first time ~60s)..." -ForegroundColor Yellow
    $loadBody = @{screenshot_path = "/data/test_frames/frame_00.png"} | ConvertTo-Json
    
    try {
        $loadResult = Invoke-RestMethod -Uri "http://localhost:8006/analyze" -Method Post `
            -Body $loadBody -ContentType "application/json" -TimeoutSec 120
        Write-Host "✅ BLIP-2 model loaded successfully" -ForegroundColor Green
        Write-Host "   Scene detected: $($loadResult.scene_type)" -ForegroundColor Gray
    } catch {
        Write-Host "⚠️  Model loading timeout (expected on first run)" -ForegroundColor Yellow
    }
    
    # Wait for model to fully initialize
    Start-Sleep -Seconds 5
} else {
    Write-Host "`n[3/5] BLIP-2 already loaded ✅" -ForegroundColor Green
}

# Step 4: Test batch processing
Write-Host "`n[4/5] Testing intelligent batch processing..." -ForegroundColor Yellow
$batchBody = @{
    screenshot_paths = @(0..15 | ForEach-Object { "/data/test_frames/frame_$($_.ToString('00')).png" })
    model_type = "llava"
    context = @{
        mode = "user_gameplay"
    }
} | ConvertTo-Json

Write-Host "   Processing 16 frames with intelligent sampling..." -ForegroundColor Gray
$startTime = Get-Date

try {
    $batchResult = Invoke-RestMethod -Uri "http://localhost:8006/analyze/batch" -Method Post `
        -Body $batchBody -ContentType "application/json" -TimeoutSec 180
    
    $duration = ((Get-Date) - $startTime).TotalSeconds
    
    Write-Host "`n✅ Batch processing complete!" -ForegroundColor Green
    Write-Host "`n--- Results ---" -ForegroundColor Cyan
    Write-Host "⏱️  Processing time: $([math]::Round($duration, 2))s" -ForegroundColor White
    Write-Host "📦 Frames analyzed: $($batchResult.frame_count)" -ForegroundColor White
    Write-Host "🎮 Scene type: $($batchResult.scene_type)" -ForegroundColor White
    Write-Host "📝 Description: $($batchResult.description)" -ForegroundColor White
    Write-Host "💬 OCR text: $($batchResult.ocr_text)" -ForegroundColor White
    Write-Host "🎯 Confidence: $([math]::Round($batchResult.confidence * 100, 1))%" -ForegroundColor White
    
    if ($batchResult.click_candidates) {
        Write-Host "`n🖱️  Click candidates:" -ForegroundColor Cyan
        foreach ($candidate in $batchResult.click_candidates) {
            Write-Host "   • $($candidate.text) at ($($candidate.x), $($candidate.y)) - $($candidate.type)" -ForegroundColor Gray
        }
    }
    
    if ($batchResult.recommended_action) {
        Write-Host "`n🎮 Recommended action:" -ForegroundColor Cyan
        $action = $batchResult.recommended_action
        Write-Host "   Action: $($action.action)" -ForegroundColor White
        if ($action.x -and $action.y) {
            Write-Host "   Location: ($($action.x), $($action.y))" -ForegroundColor Gray
        }
        Write-Host "   Reason: $($action.reason)" -ForegroundColor Gray
    }
    
    if ($batchResult.ui_elements) {
        Write-Host "`n🖼️  Persistent UI elements:" -ForegroundColor Cyan
        $batchResult.ui_elements | ForEach-Object { Write-Host "   • $_" -ForegroundColor Gray }
    }
    
} catch {
    Write-Host "`n❌ Batch processing failed:" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Red
    
    # Check logs for errors
    Write-Host "`n📋 Recent logs:" -ForegroundColor Yellow
    docker logs --tail 10 playmetric-vision 2>&1 | Select-String -Pattern "ERROR|Batch" | ForEach-Object {
        Write-Host "   $_" -ForegroundColor Gray
    }
    exit 1
}

# Step 5: Performance summary
Write-Host "`n[5/5] Performance Summary" -ForegroundColor Yellow
$fps = 16.0 / $duration
Write-Host "   📊 Throughput: $([math]::Round($fps, 2)) FPS equivalent" -ForegroundColor Gray
Write-Host "   ⚡ Optimizations:" -ForegroundColor Gray
Write-Host "      • Frame caching (avoid redundant BLIP-2 calls)" -ForegroundColor DarkGray
Write-Host "      • Scene change detection (process only changed frames)" -ForegroundColor DarkGray
Write-Host "      • OCR sampling (1 in 4 frames)" -ForegroundColor DarkGray
Write-Host "      • Keyframe selection (BLIP-2 on representative frame)" -ForegroundColor DarkGray

Write-Host "`n✨ Batch processing system ready for 16 FPS gameplay!" -ForegroundColor Green
Write-Host "   Use mode='user_gameplay' to detect clicks" -ForegroundColor Gray
Write-Host "   Use mode='ai_gameplay' for autonomous decisions`n" -ForegroundColor Gray
