# PowerShell script to check Docker installation status

Write-Host "🔍 Checking Docker Installation Status" -ForegroundColor Cyan
Write-Host ("=" * 50)

$allGood = $true

# Check Docker
Write-Host "`n🐳 Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker installed: $dockerVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker not working properly" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host "❌ Docker not found in PATH" -ForegroundColor Red
    Write-Host "   Install Docker Desktop: https://www.docker.com/products/docker-desktop" -ForegroundColor Yellow
    $allGood = $false
}

# Check Docker Compose
Write-Host "`n🐙 Checking Docker Compose..." -ForegroundColor Yellow
try {
    $composeVersion = docker-compose --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker Compose installed: $composeVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker Compose not working properly" -ForegroundColor Red
        $allGood = $false
    }
} catch {
    Write-Host "❌ Docker Compose not found" -ForegroundColor Red
    $allGood = $false
}

# Check if Docker daemon is running
Write-Host "`n⚙️  Checking Docker daemon..." -ForegroundColor Yellow
try {
    $dockerPs = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Docker daemon is running" -ForegroundColor Green
    } else {
        Write-Host "❌ Docker daemon is not running" -ForegroundColor Red
        Write-Host "   Start Docker Desktop from Start Menu" -ForegroundColor Yellow
        $allGood = $false
    }
} catch {
    Write-Host "❌ Cannot connect to Docker daemon" -ForegroundColor Red
    Write-Host "   Make sure Docker Desktop is running" -ForegroundColor Yellow
    $allGood = $false
}

# Check WSL 2
Write-Host "`n🐧 Checking WSL 2..." -ForegroundColor Yellow
try {
    $wslStatus = wsl --status 2>&1
    if ($wslStatus -match "Default Version: 2") {
        Write-Host "✅ WSL 2 is configured" -ForegroundColor Green
    } else {
        Write-Host "⚠️  WSL 2 may not be set as default" -ForegroundColor Yellow
        Write-Host "   Run: wsl --set-default-version 2" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not check WSL status" -ForegroundColor Yellow
}

# Check virtualization
Write-Host "`nChecking virtualization..." -ForegroundColor Yellow
$systemInfo = systeminfo 2>&1
if ($systemInfo -match "Hyper-V Requirements.*A hypervisor has been detected") {
    Write-Host "✅ Virtualization is enabled" -ForegroundColor Green
} else {
    Write-Host "⚠️  Virtualization status unclear" -ForegroundColor Yellow
    Write-Host "   Check Task Manager - Performance - CPU - Virtualization" -ForegroundColor Yellow
}

# Summary
Write-Host "`n" + ("=" * 50)
if ($allGood) {
    Write-Host "✅ Docker is ready to use!" -ForegroundColor Green
    Write-Host "`n🚀 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Run: docker-compose up -d" -ForegroundColor White
    Write-Host "   2. Run: python scripts/load_test_data.py" -ForegroundColor White
    Write-Host "   3. Run: python scripts/run_all_demos.py" -ForegroundColor White
} else {
    Write-Host "❌ Docker is not ready" -ForegroundColor Red
    Write-Host "`n📖 See INSTALL_DOCKER.md for installation instructions" -ForegroundColor Yellow
    Write-Host "`nQuick install:" -ForegroundColor Cyan
    Write-Host "   1. Download: https://www.docker.com/products/docker-desktop" -ForegroundColor White
    Write-Host "   2. Run installer" -ForegroundColor White
    Write-Host "   3. Restart computer" -ForegroundColor White
    Write-Host "   4. Start Docker Desktop" -ForegroundColor White
    Write-Host "   5. Run this script again to verify" -ForegroundColor White
}
