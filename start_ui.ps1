# Start Backend
Write-Host "Starting Backend Server..." -ForegroundColor Green
Set-Location backend
if (-not (Test-Path "venv")) {
    python -m venv venv
}
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --quiet
python -c "from database import init_db; init_db()" 2>$null
python seed_data.py
Start-Process python -ArgumentList "run.py" -WindowStyle Minimized
Set-Location ..

# Wait for backend to start
Start-Sleep -Seconds 3

# Start Frontend
Write-Host "Starting Frontend Server..." -ForegroundColor Green
Set-Location frontend
npm install
Start-Process npm -ArgumentList "run dev" -WindowStyle Minimized
Set-Location ..

Write-Host ""
Write-Host "Backend running on http://localhost:8000" -ForegroundColor Cyan
Write-Host "Frontend running on http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to stop..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
