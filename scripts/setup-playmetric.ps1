# Complete PlayMetric Setup with Physical Device
# Run this script to set up everything in the correct order

param(
    [switch]$SkipDeviceSetup = $false,
    [switch]$SkipBuild = $false
)

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "PlayMetric Complete Setup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Connect physical device (if not skipped)
if (-not $SkipDeviceSetup) {
    Write-Host "STEP 1: Setting up physical device..." -ForegroundColor Magenta
    Write-Host ""
    & "$PSScriptRoot\connect-physical-device.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Device setup failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host ""
    Write-Host "Press Enter to continue with Docker setup..." -ForegroundColor Yellow
    Read-Host
} else {
    Write-Host "⏭️  Skipping device setup (device should already be connected)" -ForegroundColor Yellow
    Write-Host ""
}

# Step 2: Build Docker images (if not skipped)
if (-not $SkipBuild) {
    Write-Host "STEP 2: Building Docker images (optimized parallel build)..." -ForegroundColor Magenta
    Write-Host ""
    
    # Check if base images exist
    $baseExists = docker images -q playmetric-base:latest
    if ($baseExists) {
        Write-Host "✅ Base images found, skipping base build" -ForegroundColor Green
        Write-Host "   To force rebuild base images, run: docker-compose build" -ForegroundColor Gray
        Write-Host ""
    } else {
        Write-Host "📦 Building base images (first time only, ~2-3 min)..." -ForegroundColor Yellow
        Set-Location $PSScriptRoot\..
        
        docker build -f Dockerfile.base --target base -t playmetric-base:latest .
        docker build -f Dockerfile.base --target base-adb -t playmetric-base-adb:latest .
        docker build -f Dockerfile.base --target base-ml -t playmetric-base-ml:latest .
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Base image build failed!" -ForegroundColor Red
            exit 1
        }
        Write-Host "✅ Base images built successfully!" -ForegroundColor Green
        Write-Host ""
    }
    
    Write-Host "📦 Building service images..." -ForegroundColor Yellow
    Set-Location $PSScriptRoot\..
    docker-compose build
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Service build failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ All images built successfully!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "⏭️  Skipping Docker build (using existing images)" -ForegroundColor Yellow
    Write-Host ""
}

# Step 3: Start Docker services
Write-Host "STEP 3: Starting Docker services..." -ForegroundColor Magenta
Write-Host ""
Set-Location $PSScriptRoot\..
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Docker startup failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Step 4: Verify Docker can connect to device
Write-Host ""
Write-Host "STEP 4: Verifying Docker connections..." -ForegroundColor Magenta
Write-Host ""

Write-Host "Testing emulator-manager connection:" -ForegroundColor Yellow
docker exec playmetric-emulator-manager adb devices
Write-Host ""

Write-Host "Testing agent connection:" -ForegroundColor Yellow
docker exec playmetric-agent adb devices
Write-Host ""

# Step 5: Test screen detection
Write-Host "STEP 5: Testing screen detection..." -ForegroundColor Magenta
Write-Host ""
try {
    $screenInfo = Invoke-WebRequest -Uri "http://localhost:8005/device/screen-size" -ErrorAction Stop | ConvertFrom-Json
    Write-Host "✅ Screen detected: $($screenInfo.width)x$($screenInfo.height)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Screen detection failed: $_" -ForegroundColor Yellow
    Write-Host "   Services may still be starting..." -ForegroundColor Gray
}
Write-Host ""

# Final summary
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "✅ PlayMetric Setup Complete!" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Services running:" -ForegroundColor Yellow
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""
Write-Host "Quick Links:" -ForegroundColor Yellow
Write-Host "  Dashboard:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "  API Docs:   http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  Health:     http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Open dashboard: http://localhost:3000" -ForegroundColor White
Write-Host "2. Create a new session" -ForegroundColor White
Write-Host "3. Watch AI play automatically!" -ForegroundColor White
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Yellow
Write-Host "  docker logs playmetric-agent --follow" -ForegroundColor Gray
Write-Host ""
Write-Host "To stop:" -ForegroundColor Yellow
Write-Host "  docker-compose down" -ForegroundColor Gray
Write-Host ""
