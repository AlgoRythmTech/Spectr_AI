# setup_old_laptop.ps1
#
# ONE-SHOT setup for the old-laptop host. Installs MongoDB Community, seeds the
# 2,881-section statute corpus, installs Python + Node dependencies, starts the
# backend via supervisor, and starts the frontend dev server.
#
# HOW TO RUN
# ----------
# 1. Copy the entire Associate_Research folder to the old laptop
#    (USB stick, Google Drive, GitHub clone — whatever's fastest).
# 2. Open PowerShell AS ADMINISTRATOR on the old laptop.
# 3. cd <path>\Associate_Research
# 4. Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# 5. .\setup_old_laptop.ps1
#
# On completion:
#   Backend  → http://localhost:8000
#   Frontend → http://localhost:3000
#   Mongo    → mongodb://localhost:27017 (2,881 statute docs loaded)
#
# The backend is started under a supervisor so if the Python process crashes,
# it auto-restarts. To stop everything:
#   cd backend; .\backend_stop.ps1
#   Get-Process node | Stop-Process  (optional — frontend dev server)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'

function Section([string]$msg) {
    Write-Host ""
    Write-Host "==== $msg ====" -ForegroundColor Cyan
}

# ─── 1. Install MongoDB Community ──────────────────────────────────────
Section "1. MongoDB Community Server"
$mongod = Get-Command mongod -ErrorAction SilentlyContinue
if ($mongod) {
    Write-Host "MongoDB already installed at $($mongod.Source)" -ForegroundColor Green
} else {
    Write-Host "Installing MongoDB via winget..."
    winget install MongoDB.Server --accept-source-agreements --accept-package-agreements --silent
    if ($LASTEXITCODE -ne 0) {
        throw "MongoDB install failed — run 'winget install MongoDB.Server' manually"
    }
    # MongoDB installer registers a Windows service named "MongoDB"; give it a beat to start.
    Start-Sleep -Seconds 3
}

# Ensure the service is running
$svc = Get-Service -Name "MongoDB" -ErrorAction SilentlyContinue
if ($svc) {
    if ($svc.Status -ne "Running") {
        Write-Host "Starting MongoDB service..."
        Start-Service -Name "MongoDB"
    }
    Write-Host "MongoDB service status: $($svc.Status)" -ForegroundColor Green
} else {
    Write-Host "No MongoDB Windows service found. Starting mongod manually..."
    $dataDir = "C:\data\db"
    if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }
    Start-Process -FilePath "mongod" -ArgumentList "--dbpath", $dataDir -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# ─── 2. Install Python 3.12 if missing ─────────────────────────────────
Section "2. Python 3.12"
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    $pyver = & python --version 2>&1
    Write-Host "Python already installed: $pyver" -ForegroundColor Green
} else {
    Write-Host "Installing Python 3.12 via winget..."
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements --silent
    $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
}

# ─── 3. Install Node.js 20 if missing ──────────────────────────────────
Section "3. Node.js 20"
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    $nodever = & node --version 2>&1
    Write-Host "Node already installed: $nodever" -ForegroundColor Green
} else {
    Write-Host "Installing Node.js 20 via winget..."
    winget install OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements --silent
    $env:PATH = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
}

# ─── 4. Backend .env — point at local Mongo ────────────────────────────
Section "4. Configure backend/.env for local MongoDB"
$envPath = Join-Path $backend '.env'
if (-not (Test-Path $envPath)) {
    throw "backend/.env not found — did you copy the full project folder?"
}
$envContent = Get-Content $envPath -Raw
$updated = $envContent

# Flip to local MongoDB — overwrites the Atlas URL
if ($updated -match "MONGO_URL=") {
    $updated = $updated -replace "MONGO_URL=.*", "MONGO_URL=mongodb://localhost:27017"
} else {
    $updated += "`nMONGO_URL=mongodb://localhost:27017"
}

# Ensure USE_FIRESTORE=0
if ($updated -match "USE_FIRESTORE=") {
    $updated = $updated -replace "USE_FIRESTORE=.*", "USE_FIRESTORE=0"
} else {
    $updated += "`nUSE_FIRESTORE=0"
}

# Local mode skips TLS for Mongo
if ($updated -notmatch "MONGO_LOCAL=") {
    $updated += "`nMONGO_LOCAL=1"
}

Set-Content -Path $envPath -Value $updated -Encoding UTF8
Write-Host ".env updated: MONGO_URL=mongodb://localhost:27017, USE_FIRESTORE=0" -ForegroundColor Green

# ─── 5. pip install backend dependencies ───────────────────────────────
Section "5. Python dependencies (this takes 5-10 min)"
Push-Location $backend
try {
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
} finally {
    Pop-Location
}

# ─── 6. Seed statutes into local MongoDB ───────────────────────────────
Section "6. Seeding 2,881 statute sections into local MongoDB"
Push-Location $backend
try {
    python seed_statutes_to_mongo.py --commit --wipe
} finally {
    Pop-Location
}

# ─── 7. npm install frontend ───────────────────────────────────────────
Section "7. Frontend npm install (5-10 min)"
Push-Location $frontend
try {
    npm install
} finally {
    Pop-Location
}

# ─── 8. Start backend under supervisor ─────────────────────────────────
Section "8. Starting backend via supervisor"
Push-Location $backend
try {
    & powershell -ExecutionPolicy Bypass -File .\backend_start.ps1
} finally {
    Pop-Location
}

# Wait for backend to be healthy
Write-Host "Waiting for backend health check..." -NoNewline
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        if ($r.StatusCode -eq 200) { $ready = $true; break }
    } catch { Write-Host "." -NoNewline }
}
Write-Host ""
if ($ready) {
    Write-Host "Backend is UP at http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "Backend did not respond within 2 min. Check backend/backend_live.log." -ForegroundColor Yellow
}

# ─── 9. Start frontend in a new window ─────────────────────────────────
Section "9. Starting frontend"
$frontendCmd = "cd `"$frontend`"; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# ─── Done ──────────────────────────────────────────────────────────────
Section "SETUP COMPLETE"
Write-Host ""
Write-Host "Backend :  http://localhost:8000     (health: /health)"
Write-Host "Frontend:  http://localhost:3000     (opens in a few seconds)"
Write-Host "MongoDB :  mongodb://localhost:27017 (statutes seeded)"
Write-Host ""
Write-Host "To stop the backend: cd backend; .\backend_stop.ps1"
Write-Host "To reseed statutes:  cd backend; python seed_statutes_to_mongo.py --commit --wipe"
Write-Host ""
Write-Host "You are ready for the client demo. Leave this laptop powered on and connected." -ForegroundColor Cyan
