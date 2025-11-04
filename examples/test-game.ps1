# Example: Test a game APK with PlayMetric

$APK_PATH = "/apks/your-game.apk"
$PACKAGE_NAME = "com.yourcompany.yourgame"
$DURATION = 30  # minutes

Write-Host "===================================" -ForegroundColor Cyan
Write-Host "PlayMetric Game Testing Example" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# Function to make API calls
function Invoke-PlayMetricAPI {
    param(
        [string]$Endpoint,
        [string]$Method = "GET",
        [hashtable]$Body = $null
    )
    
    $uri = "http://localhost:8000$Endpoint"
    $params = @{
        Uri = $uri
        Method = $Method
        ContentType = "application/json"
    }
    
    if ($Body) {
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }
    
    try {
        return Invoke-RestMethod @params
    } catch {
        Write-Host "Error: $_" -ForegroundColor Red
        return $null
    }
}

# 1. Check system health
Write-Host "1. Checking system health..." -ForegroundColor Yellow
$health = Invoke-PlayMetricAPI -Endpoint "/health"
if ($health) {
    Write-Host "✓ System is healthy" -ForegroundColor Green
    $health.services | Format-Table
} else {
    Write-Host "✗ System health check failed" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 2

# 2. Install APK
Write-Host ""
Write-Host "2. Installing APK..." -ForegroundColor Yellow
$install = Invoke-PlayMetricAPI -Endpoint "/api/install-apk" -Method POST -Body @{
    apk_path = $APK_PATH
}

if ($install) {
    Write-Host "✓ APK installed successfully" -ForegroundColor Green
} else {
    Write-Host "✗ APK installation failed" -ForegroundColor Red
    exit 1
}

Start-Sleep -Seconds 5

# 3. Start testing session
Write-Host ""
Write-Host "3. Starting testing session..." -ForegroundColor Yellow
$session = Invoke-PlayMetricAPI -Endpoint "/api/start-session" -Method POST -Body @{
    package_name = $PACKAGE_NAME
    agent_mode = "heuristic"
    duration_minutes = $DURATION
    auto_install = $false
}

if ($session) {
    $sessionId = $session.session.session_id
    Write-Host "✓ Session started: $sessionId" -ForegroundColor Green
    Write-Host "  Package: $PACKAGE_NAME" -ForegroundColor Cyan
    Write-Host "  Agent: heuristic" -ForegroundColor Cyan
    Write-Host "  Duration: $DURATION minutes" -ForegroundColor Cyan
} else {
    Write-Host "✗ Failed to start session" -ForegroundColor Red
    exit 1
}

# 4. Monitor progress
Write-Host ""
Write-Host "4. Monitoring session..." -ForegroundColor Yellow
Write-Host "   You can watch the emulator at: http://localhost:6080" -ForegroundColor Cyan
Write-Host ""

$startTime = Get-Date
$endTime = $startTime.AddMinutes($DURATION)

Write-Host "Session will run until: $endTime" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop early" -ForegroundColor Yellow
Write-Host ""

# Monitor every 60 seconds
while ((Get-Date) -lt $endTime) {
    $status = Invoke-PlayMetricAPI -Endpoint "/api/sessions/$sessionId"
    
    if ($status) {
        $elapsed = [math]::Round($status.duration_seconds / 60, 1)
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Session Status:" -ForegroundColor Cyan
        Write-Host "  Elapsed: $elapsed min" -ForegroundColor White
        Write-Host "  Actions: $($status.metrics.actions_performed)" -ForegroundColor White
        Write-Host "  Crashes: $($status.metrics.crashes_detected)" -ForegroundColor White
        Write-Host ""
    }
    
    Start-Sleep -Seconds 60
}

# 5. Stop session
Write-Host ""
Write-Host "5. Stopping session..." -ForegroundColor Yellow
$stop = Invoke-PlayMetricAPI -Endpoint "/api/stop-session" -Method POST -Body @{
    session_id = $sessionId
    save_analytics = $true
}

if ($stop) {
    Write-Host "✓ Session stopped successfully" -ForegroundColor Green
} else {
    Write-Host "✗ Failed to stop session" -ForegroundColor Red
}

Start-Sleep -Seconds 3

# 6. Get analytics
Write-Host ""
Write-Host "6. Fetching analytics..." -ForegroundColor Yellow
$analytics = Invoke-PlayMetricAPI -Endpoint "/api/analytics/$sessionId"

if ($analytics) {
    Write-Host "✓ Analytics retrieved" -ForegroundColor Green
    Write-Host ""
    
    # Display retention estimates
    Write-Host "=== RETENTION ESTIMATES ===" -ForegroundColor Cyan
    $retention = $analytics.retention.retention_estimates
    Write-Host "  Day 1:  $($retention.day_1.percentage)" -ForegroundColor White
    Write-Host "  Day 7:  $($retention.day_7.percentage)" -ForegroundColor White
    Write-Host "  Day 30: $($retention.day_30.percentage)" -ForegroundColor White
    Write-Host ""
    
    # Display difficulty summary
    if ($analytics.difficulty.total_levels -gt 0) {
        Write-Host "=== DIFFICULTY ANALYSIS ===" -ForegroundColor Cyan
        Write-Host "  Total Levels: $($analytics.difficulty.total_levels)" -ForegroundColor White
        
        if ($analytics.difficulty.hardest_levels) {
            Write-Host "  Hardest Levels:" -ForegroundColor Yellow
            foreach ($level in $analytics.difficulty.hardest_levels[0..2]) {
                Write-Host "    - $($level.level): $([math]::Round($level.score, 2))" -ForegroundColor White
            }
        }
        Write-Host ""
    }
    
    # Display churn risks
    if ($analytics.retention.churn_risks) {
        Write-Host "=== CHURN RISKS ===" -ForegroundColor Cyan
        foreach ($risk in $analytics.retention.churn_risks) {
            $color = if ($risk.severity -eq "high") { "Red" } else { "Yellow" }
            Write-Host "  [$($risk.severity.ToUpper())] $($risk.factor)" -ForegroundColor $color
            Write-Host "    $($risk.description)" -ForegroundColor White
            Write-Host "    Impact: $($risk.impact)" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    # Save to file
    $outputFile = ".\analytics_$sessionId.json"
    $analytics | ConvertTo-Json -Depth 10 | Out-File $outputFile
    Write-Host "Full analytics saved to: $outputFile" -ForegroundColor Green
    
} else {
    Write-Host "✗ Failed to retrieve analytics" -ForegroundColor Red
}

Write-Host ""
Write-Host "===================================" -ForegroundColor Green
Write-Host "Testing Complete!" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""
Write-Host "Results saved in:" -ForegroundColor Cyan
Write-Host "  - Screenshots: .\data\screenshots\$sessionId\" -ForegroundColor White
Write-Host "  - Analytics: .\data\analytics\$sessionId\" -ForegroundColor White
Write-Host "  - Logs: .\data\logs\" -ForegroundColor White
