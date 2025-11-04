# Test Advanced RL Agent Integration
# PowerShell script to test the new RL system

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "PlayMetric V2 - RL System Test" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$ORCHESTRATOR_URL = "http://localhost:8000"
$AGENT_URL = "http://localhost:8004"
$POSTGRES_URL = "localhost:5432"

Write-Host "[1/6] Checking Services..." -ForegroundColor Yellow

# Check Orchestrator
try {
    $orchestratorHealth = Invoke-RestMethod -Uri "$ORCHESTRATOR_URL/health" -Method Get
    Write-Host "✓ Orchestrator: $($orchestratorHealth.status)" -ForegroundColor Green
} catch {
    Write-Host "✗ Orchestrator not responding" -ForegroundColor Red
    exit 1
}

# Check Agent
try {
    $agentHealth = Invoke-RestMethod -Uri "$AGENT_URL/health" -Method Get
    Write-Host "✓ Agent: $($agentHealth.status)" -ForegroundColor Green
    Write-Host "  - DB Connected: $($agentHealth.db_connected)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Agent not responding" -ForegroundColor Red
    exit 1
}

# Check PostgreSQL
Write-Host "[2/6] Checking Database..." -ForegroundColor Yellow
try {
    docker exec playmetric-postgres pg_isready -U playmetric
    Write-Host "✓ PostgreSQL is ready" -ForegroundColor Green
    
    # Check schema
    $tableCount = docker exec playmetric-postgres psql -U playmetric -d playmetric -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';"
    Write-Host "  - Tables: $($tableCount.Trim())" -ForegroundColor Gray
} catch {
    Write-Host "✗ PostgreSQL not responding" -ForegroundColor Red
    exit 1
}

# Create test game
Write-Host "[3/6] Creating Test Game..." -ForegroundColor Yellow

$testGame = @{
    package_name = "com.example.testpuzzle"
    display_name = "Test Puzzle Game"
    genre = "puzzle"
} | ConvertTo-Json

try {
    $gameQuery = @"
INSERT INTO games (package_name, display_name, genre)
VALUES ('com.example.testpuzzle', 'Test Puzzle Game', 'puzzle')
ON CONFLICT (package_name) DO UPDATE SET display_name = 'Test Puzzle Game'
RETURNING id;
"@
    
    $gameId = docker exec playmetric-postgres psql -U playmetric -d playmetric -t -c $gameQuery
    $gameId = $gameId.Trim()
    Write-Host "✓ Game ID: $gameId" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create game" -ForegroundColor Red
    exit 1
}

# Create test game version
Write-Host "[4/6] Creating Game Version..." -ForegroundColor Yellow

try {
    $versionQuery = @"
INSERT INTO game_versions (game_id, version_code, version_name, apk_path, apk_hash)
VALUES ('$gameId', 1, '1.0.0', '/apks/test.apk', 'abc123')
ON CONFLICT (game_id, version_code) DO UPDATE SET version_name = '1.0.0'
RETURNING id;
"@
    
    $versionId = docker exec playmetric-postgres psql -U playmetric -d playmetric -t -c $versionQuery
    $versionId = $versionId.Trim()
    Write-Host "✓ Version ID: $versionId" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create version" -ForegroundColor Red
    exit 1
}

# Create test session
Write-Host "[5/6] Creating Test Session..." -ForegroundColor Yellow

try {
    $sessionQuery = @"
INSERT INTO sessions (game_version_id, session_name, agent_mode, status, config)
VALUES ('$versionId', 'RL Test Session', 'advanced_rl', 'running', '{}')
RETURNING id;
"@
    
    $sessionId = docker exec playmetric-postgres psql -U playmetric -d playmetric -t -c $sessionQuery
    $sessionId = $sessionId.Trim()
    Write-Host "✓ Session ID: $sessionId" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to create session" -ForegroundColor Red
    exit 1
}

# Start RL agent
Write-Host "[6/6] Starting RL Agent..." -ForegroundColor Yellow

$agentConfig = @{
    agent_mode = "advanced_rl"
    session_id = $sessionId
    game_id = $gameId
    package_name = "com.example.testpuzzle"
    enable_training = $true
    training_interval = 10
} | ConvertTo-Json

try {
    $startResponse = Invoke-RestMethod -Uri "$AGENT_URL/play/start" -Method Post -ContentType "application/json" -Body $agentConfig
    Write-Host "✓ Agent started: $($startResponse.agent)" -ForegroundColor Green
    Write-Host "  - Training: $($startResponse.training_enabled)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed to start agent: $_" -ForegroundColor Red
    exit 1
}

# Wait and check status
Write-Host ""
Write-Host "Waiting 10 seconds for RL agent to collect experiences..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

# Check agent stats
Write-Host ""
Write-Host "Agent Statistics:" -ForegroundColor Yellow
try {
    $stats = Invoke-RestMethod -Uri "$AGENT_URL/agent/statistics" -Method Get
    Write-Host "  - Agent Type: $($stats.agent_type)" -ForegroundColor Gray
    Write-Host "  - Episodes: $($stats.episodes)" -ForegroundColor Gray
    Write-Host "  - Steps: $($stats.steps)" -ForegroundColor Gray
    Write-Host "  - Epsilon: $([math]::Round($stats.epsilon, 4))" -ForegroundColor Gray
    Write-Host "  - Memory Size: $($stats.memory_size)" -ForegroundColor Gray
    Write-Host "  - Training Enabled: $($stats.training_enabled)" -ForegroundColor Gray
} catch {
    Write-Host "  - Could not fetch stats" -ForegroundColor Red
}

# Check memory stats
Write-Host ""
Write-Host "Experience Replay Memory:" -ForegroundColor Yellow
try {
    $memory = Invoke-RestMethod -Uri "$AGENT_URL/agent/memory/stats" -Method Get
    Write-Host "  - Size: $($memory.size)" -ForegroundColor Gray
    Write-Host "  - Capacity: $($memory.capacity)" -ForegroundColor Gray
    Write-Host "  - Utilization: $([math]::Round($memory.utilization, 2))%" -ForegroundColor Gray
    Write-Host "  - Alpha: $($memory.alpha)" -ForegroundColor Gray
    Write-Host "  - Beta: $([math]::Round($memory.beta, 4))" -ForegroundColor Gray
} catch {
    Write-Host "  - Could not fetch memory stats" -ForegroundColor Red
}

# Check database experiences
Write-Host ""
Write-Host "Database Check:" -ForegroundColor Yellow
try {
    $expCount = docker exec playmetric-postgres psql -U playmetric -d playmetric -t -c "SELECT COUNT(*) FROM rl_experiences WHERE game_id='$gameId';"
    Write-Host "  - RL Experiences Stored: $($expCount.Trim())" -ForegroundColor Gray
} catch {
    Write-Host "  - Could not check database" -ForegroundColor Red
}

# Stop agent
Write-Host ""
Write-Host "Stopping agent..." -ForegroundColor Yellow
try {
    $stopResponse = Invoke-RestMethod -Uri "$AGENT_URL/play/stop" -Method Post
    Write-Host "✓ Agent stopped" -ForegroundColor Green
    Write-Host "  - Final Steps: $($stopResponse.statistics.steps)" -ForegroundColor Gray
    Write-Host "  - Memory Size: $($stopResponse.statistics.memory_size)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Failed to stop agent" -ForegroundColor Red
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Check agent logs: docker logs playmetric-agent" -ForegroundColor Gray
Write-Host "2. Query experiences: docker exec playmetric-postgres psql -U playmetric -d playmetric -c 'SELECT * FROM rl_experiences LIMIT 5;'" -ForegroundColor Gray
Write-Host "3. View models: docker exec playmetric-postgres psql -U playmetric -d playmetric -c 'SELECT * FROM rl_models;'" -ForegroundColor Gray
Write-Host ""
