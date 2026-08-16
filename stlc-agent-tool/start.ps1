$ErrorActionPreference = "Stop"

# Change to the script's directory
$PSScriptRoot = Split-Path -Parent -MyInvocation.MyCommand.Definition
Set-Location $PSScriptRoot

Write-Host "==================================" -ForegroundColor Cyan
Write-Host " Starting STLC Agentic Tool Setup " -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

Write-Host "Cleaning up lingering processes on ports 8000 and 5173..." -ForegroundColor Yellow
$ports = @(8000, 5173)
foreach ($port in $ports) {
    $processes = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid_val in $processes) {
        Stop-Process -Id $pid_val -Force -ErrorAction SilentlyContinue
    }
}

# 1. Backend Setup
Write-Host "`n[1/2] Building Backend..." -ForegroundColor Green
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "'uv' is not installed. Please install it first."
    exit 1
}

Set-Location backend
uv sync
Set-Location ..

Write-Host "Starting FastAPI Backend in a new window..." -ForegroundColor Green
$env:PYTHONPATH = "."
$backendProcess = Start-Process -FilePath "backend\.venv\Scripts\python.exe" -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload" -PassThru

Write-Host "Waiting for backend to fully start..." -ForegroundColor Yellow
$timeout = 180
$sw = [Diagnostics.Stopwatch]::StartNew()
$backendUp = $false

while ($sw.Elapsed.TotalSeconds -lt $timeout) {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/docs" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $backendUp = $true
            break
        }
    } catch {
        # Backend not up yet
    }
    Start-Sleep -Seconds 1
}

if (-not $backendUp) {
    if ($backendProcess -and !$backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Error "Backend failed to start within 180 seconds."
    exit 1
}

Write-Host "Backend startup complete!" -ForegroundColor Green

# 2. Frontend Setup
Write-Host "`n[2/2] Building Frontend..." -ForegroundColor Green
if (!(Get-Command npm -ErrorAction SilentlyContinue)) {
    if ($backendProcess -and !$backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force
    }
    Write-Error "'npm' is not installed. Please install Node.js."
    exit 1
}

Set-Location frontend
npm install

Write-Host "Starting React Frontend..." -ForegroundColor Green
try {
    npm run dev
} finally {
    if ($backendProcess -and !$backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
