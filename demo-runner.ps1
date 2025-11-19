# PowerShell version of demo runner for Windows
$ErrorActionPreference = "Stop"

Write-Host "BGP Conflict Detection Full Test Suite" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Check dependencies
Write-Host "`nChecking dependencies..." -ForegroundColor Yellow
if (-not (Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] docker-compose required" -ForegroundColor Red
    exit 1
}
if (-not (Get-Command python3 -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] python3 required" -ForegroundColor Red
    exit 1
}

# Start infrastructure
Write-Host "`nStarting infrastructure..." -ForegroundColor Yellow
docker-compose up -d

# Wait for Infrahub
Write-Host "`nWaiting for Infrahub to be ready..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts -and -not $ready) {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/info" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] Infrahub is ready!" -ForegroundColor Green
            $ready = $true
        }
    } catch {
        Write-Host "  Attempt $attempt/$maxAttempts..."
        Start-Sleep -Seconds 2
    }
}

if (-not $ready) {
    Write-Host "[ERROR] Infrahub not ready after $($maxAttempts * 2) seconds" -ForegroundColor Red
    exit 1
}

# Install Python dependencies
Write-Host "`nInstalling Python dependencies..." -ForegroundColor Yellow
python3 -m pip install -q httpx pyyaml "gql[requests]" infrahub-sdk

# Load test data
Write-Host "`nLoading test data..." -ForegroundColor Yellow
python3 scripts/load_test_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to load test data" -ForegroundColor Red
    exit 1
}

# Run demo scenarios
Write-Host "`nRunning demo scenarios..." -ForegroundColor Yellow
python3 scripts/run_all_demos.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Demo scenarios failed" -ForegroundColor Red
    exit 1
}

# Cleanup
Write-Host "`nCleaning up..." -ForegroundColor Yellow
docker-compose down

Write-Host "`nDemo suite complete!" -ForegroundColor Green

