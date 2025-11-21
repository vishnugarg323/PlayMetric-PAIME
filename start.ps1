# PlayMetric-PAIME - AI Learning & Playing System
# Quick Start Script

Write-Host "`n=== PlayMetric-PAIME - AI Game Testing Platform ===" -ForegroundColor Cyan
Write-Host "New Architecture: Learning Mode + Playing Mode`n" -ForegroundColor Yellow

# Check Docker
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker not found. Please install Docker Desktop" -ForegroundColor Red
    exit 1
}

Write-Host "📋 Available Modes:" -ForegroundColor Cyan
Write-Host "  1. Learning Mode - Learn from gameplay videos (offline)" -ForegroundColor White
Write-Host "  2. Playing Mode  - AI plays game with decision engine" -ForegroundColor White
Write-Host "  3. Full System   - Start everything`n" -ForegroundColor White

$choice = Read-Host "Select mode (1/2/3)"

switch ($choice) {
    "1" {
        Write-Host "`n🧠 Starting Learning Mode..." -ForegroundColor Green
        docker compose up -d postgres learning vision
        Start-Sleep -Seconds 5
        
        Write-Host "`n✅ Learning Mode Ready!" -ForegroundColor Green
        Write-Host "📊 Dashboard: http://localhost:3000/learning.html" -ForegroundColor Cyan
        Write-Host "📤 Upload gameplay video to start learning`n" -ForegroundColor Yellow
    }
    
    "2" {
        Write-Host "`n🎮 Starting Playing Mode..." -ForegroundColor Green
        docker compose up -d postgres ai-player vision observation
        Start-Sleep -Seconds 5
        
        Write-Host "`n✅ Playing Mode Ready!" -ForegroundColor Green
        Write-Host "📊 Dashboard: http://localhost:3000/player.html" -ForegroundColor Cyan
        Write-Host "🕹️  Click 'Start Playing' to watch AI play`n" -ForegroundColor Yellow
    }
    
    "3" {
        Write-Host "`n🚀 Starting Full System..." -ForegroundColor Green
        docker compose up -d
        Start-Sleep -Seconds 5
        
        Write-Host "`n✅ Full System Ready!" -ForegroundColor Green
        Write-Host "📊 Learning: http://localhost:3000/learning.html" -ForegroundColor Cyan
        Write-Host "📊 Playing:  http://localhost:3000/player.html" -ForegroundColor Cyan
        Write-Host "📊 Main:     http://localhost:3000`n" -ForegroundColor Cyan
    }
    
    default {
        Write-Host "❌ Invalid choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host "📝 Logs:" -ForegroundColor Yellow
Write-Host "  docker compose logs -f learning" -ForegroundColor Gray
Write-Host "  docker compose logs -f ai-player" -ForegroundColor Gray
Write-Host "  docker compose logs -f vision`n" -ForegroundColor Gray

Write-Host "🛑 Stop:" -ForegroundColor Yellow
Write-Host "  docker compose down`n" -ForegroundColor Gray
