# PlayMetric Optimized Build Script
# Builds base images + all services with parallel execution
# 
# NOTE: This is automatically called by setup-playmetric.ps1
# You only need to run this directly if rebuilding without setup
#
# Usage:
#   .\build-optimized.ps1              # Full parallel build
#   .\build-optimized.ps1 -BaseOnly    # Only rebuild base images

param(
    [switch]$BaseOnly = $false
)

Write-Host "🚀 PlayMetric Optimized Build" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Step 1: Build base images first (they're used by all services)
Write-Host "📦 Step 1/3: Building base images..." -ForegroundColor Yellow
Write-Host "Building base image (common dependencies)..." -ForegroundColor Gray
docker build -f Dockerfile.base --target base -t playmetric-base:latest . 

Write-Host "Building base-adb image (with ADB support)..." -ForegroundColor Gray
docker build -f Dockerfile.base --target base-adb -t playmetric-base-adb:latest .

Write-Host "Building base-ml image (with CV/ML support)..." -ForegroundColor Gray
docker build -f Dockerfile.base --target base-ml -t playmetric-base-ml:latest .

Write-Host "✅ Base images built successfully!" -ForegroundColor Green
Write-Host ""

# Exit if only building base images
if ($BaseOnly) {
    Write-Host "✅ Base-only build complete!" -ForegroundColor Green
    Write-Host "Run without -BaseOnly to build service images" -ForegroundColor Gray
    exit 0
}

# Step 2: Build all service images in parallel (much faster!)
Write-Host "📦 Step 2/3: Building service images in parallel..." -ForegroundColor Yellow
Write-Host "Starting parallel builds for 5 services..." -ForegroundColor Gray

$jobs = @()

# Agent service (depends on base-ml)
$jobs += Start-Job -ScriptBlock {
    param($context, $dockerfile, $tag)
    docker build --build-arg BASE_IMAGE=playmetric-base-ml:latest -f $dockerfile -t $tag $context
} -ArgumentList ".\agent", ".\agent\Dockerfile", "playmetric-agent:latest"

# Orchestrator service (depends on base-adb)
$jobs += Start-Job -ScriptBlock {
    param($context, $dockerfile, $tag)
    docker build --build-arg BASE_IMAGE=playmetric-base-adb:latest -f $dockerfile -t $tag $context
} -ArgumentList ".\orchestrator", ".\orchestrator\Dockerfile", "playmetric-orchestrator:latest"

# Observation service (depends on base-adb)
$jobs += Start-Job -ScriptBlock {
    param($context, $dockerfile, $tag)
    docker build --build-arg BASE_IMAGE=playmetric-base-adb:latest -f $dockerfile -t $tag $context
} -ArgumentList ".\observation", ".\observation\Dockerfile", "playmetric-observation:latest"

# Emulator manager (depends on base)
$jobs += Start-Job -ScriptBlock {
    param($context, $dockerfile, $tag, $root)
    Set-Location $root
    docker build --build-arg BASE_IMAGE=playmetric-base:latest -f $dockerfile -t $tag .
} -ArgumentList ".", ".\emulator_manager\Dockerfile", "playmetric-emulator-manager:latest", $PWD

# Dashboard (independent React build)
$jobs += Start-Job -ScriptBlock {
    param($context, $dockerfile, $tag)
    docker build -f $dockerfile -t $tag $context
} -ArgumentList ".\dashboard", ".\dashboard\Dockerfile", "playmetric-dashboard:latest"

# Wait for all builds to complete
$jobs | ForEach-Object {
    $_ | Wait-Job | Out-Null
    $output = $_ | Receive-Job
    if ($output) {
        Write-Host $output
    }
    if ($_.State -eq "Failed") {
        Write-Host "❌ Build failed!" -ForegroundColor Red
        $jobs | Stop-Job
        exit 1
    }
}

$jobs | Remove-Job

Write-Host "✅ All service images built successfully!" -ForegroundColor Green
Write-Host ""

# Step 3: Tag images for docker-compose
Write-Host "📦 Step 3/3: Tagging images for docker-compose..." -ForegroundColor Yellow
docker tag playmetric-agent:latest playmetric-agent:latest
docker tag playmetric-orchestrator:latest playmetric-orchestrator:latest
docker tag playmetric-observation:latest playmetric-observation:latest
docker tag playmetric-emulator-manager:latest playmetric-emulator-manager:latest
docker tag playmetric-dashboard:latest playmetric-dashboard:latest

Write-Host "✅ Images tagged successfully!" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "🎉 Build Complete!" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Host ""
Write-Host "Built images:" -ForegroundColor Cyan
Write-Host "  📦 playmetric-base:latest (common dependencies)" -ForegroundColor Gray
Write-Host "  📦 playmetric-base-adb:latest (with ADB)" -ForegroundColor Gray
Write-Host "  📦 playmetric-base-ml:latest (with CV/ML)" -ForegroundColor Gray
Write-Host "  🤖 playmetric-agent:latest" -ForegroundColor Gray
Write-Host "  🎮 playmetric-orchestrator:latest" -ForegroundColor Gray
Write-Host "  👁️  playmetric-observation:latest" -ForegroundColor Gray
Write-Host "  📱 playmetric-emulator-manager:latest" -ForegroundColor Gray
Write-Host "  📊 playmetric-dashboard:latest" -ForegroundColor Gray
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. docker-compose up -d" -ForegroundColor White
Write-Host "  2. Wait for services to start (check: docker-compose ps)" -ForegroundColor White
Write-Host "  3. Open dashboard: http://localhost:3000" -ForegroundColor White
Write-Host ""
